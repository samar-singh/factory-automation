"""True Agentic Orchestrator - Autonomous AI with tool usage (Refactored with shared tools)"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

# Removed SDK imports - using direct OpenAI API for true approval capability
# from agents import Agent, Runner, trace  # SDK executes immediately - can't intercept
from openai import AsyncOpenAI

from ..factory_config.settings import settings
from ..factory_database.connection import get_db
from ..factory_database.models import ActionAudit
from ..factory_database.vector_db import ChromaDBClient
from ..factory_utils.trace_monitor import trace_monitor
from .action_classifier import ActionClassifier, ActionType
from .image_processor_agent import ImageProcessorAgent
from .mock_gmail_agent import MockGmailAgent
from .order_processor_agent import OrderProcessorAgent
from .tools.tool_factory import ToolFactory
from .two_tier_executor import TwoTierExecutor

# Import select functions from proposal_engine for reasoning generation
from .proposal_engine import ProposalEngine

# Import validation system for enforcing tool order
from .validation_agent import ValidationAgent
from .validation_rules import VALIDATION_RULES

logger = logging.getLogger(__name__)


class AgenticOrchestratorV3:
    """Fully autonomous orchestrator using OpenAI Agents SDK with shared tools"""

    def __init__(self, chromadb_client: ChromaDBClient, use_mock_gmail: bool = True):
        """Initialize with ChromaDB and create autonomous orchestrator with true approval capability"""
        self.chromadb_client = chromadb_client
        # Removed Runner - using direct API for true interception
        self.is_monitoring = False
        self.approval_mode = True  # Now actually works with direct API approach

        # Load business email configuration
        self.business_emails = settings.config.get("business_emails", {})
        self.email_configs = {}  # Map email address to full config

        # Process email configurations
        for email_config in self.business_emails.get("emails", []):
            address = email_config.get("address")
            if address:
                self.email_configs[address.lower()] = {
                    "description": email_config.get("description", ""),
                    "likely_intents": email_config.get("likely_intents", []),
                    "confidence_boost": email_config.get("confidence_boost", 0.0),
                }

        # Extract just the addresses for compatibility
        self.primary_emails = list(self.email_configs.keys())

        # Pattern learning config
        self.pattern_config = self.business_emails.get(
            "pattern_learning",
            {
                "enabled": True,
                "min_count_for_pattern": 3,
                "max_confidence": 0.95,
                "initial_confidence": 0.6,
                "confidence_increment": 0.05,
            },
        )

        logger.info(
            f"Monitoring {len(self.primary_emails)} business emails with descriptions"
        )
        for email, config in self.email_configs.items():
            logger.info(f"  {email}: {config['description'][:50]}...")

        # Initialize mock Gmail for testing (can be disabled)
        if use_mock_gmail:
            self.gmail_agent = MockGmailAgent()
        else:
            self.gmail_agent = None
            logger.info("Mock Gmail disabled - no automatic email processing")

        # Initialize new processors
        self.order_processor = OrderProcessorAgent(chromadb_client)
        self.image_processor = ImageProcessorAgent(chromadb_client)

        # Initialize OpenAI client for both classification AND execution (replacing SDK)
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)

        # Tool call tracking
        self.tool_call_history = []
        
        # Phase 3: Action tracking and workflow management
        self.action_classifier = ActionClassifier()
        self.proposal_engine = ProposalEngine()  # For reasoning generation
        self.current_workflow_id = None
        self.workflow_actions = []  # Track actions for current workflow
        
        # Phase 4: Two-tier execution system
        self.two_tier_executor = TwoTierExecutor(self.action_classifier)
        self.pending_actions = []  # Track pending irreversible actions
        self.auto_executed_actions = []  # Track auto-executed reversible actions
        
        # Initialize validation agent for tool call validation
        self.validator = ValidationAgent(VALIDATION_RULES)
        self.validator.set_strict_mode(True)  # Enable strict validation
        logger.info("Initialized ValidationAgent for tool call validation")

        # Create tool factory with all dependencies
        self.tool_factory = ToolFactory(
            mode="execute",  # V3 executes actions
            chromadb_client=chromadb_client,
            gmail_agent=self.gmail_agent,
            openai_client=self.openai_client,
            order_processor=self.order_processor,
            image_processor=self.image_processor,
            email_configs=self.email_configs,
            pattern_config=self.pattern_config,
        )

        # Get all tools for V3
        self.tools = self.tool_factory.get_tools_for_v3()
        
        # Build tool map and schemas for direct API usage
        self.tool_map = {}
        self.tool_schemas = []
        for tool in self.tools:
            # Map tool names to functions for execution
            self.tool_map[tool.name] = tool.function if hasattr(tool, 'function') else tool
            
            # Build OpenAI-compatible tool schema
            # Check for params_json_schema (wrapped tools) or parameters (original tools)
            params = getattr(tool, 'params_json_schema', None) or getattr(tool, 'parameters', None)
            if not params:
                params = {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            
            tool_schema = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": getattr(tool, 'description', ''),
                    "parameters": params
                }
            }
            self.tool_schemas.append(tool_schema)
        
        # Store instructions for use in API calls
        self.agent_instructions = self._get_agent_instructions()
        self.model = "gpt-4o"  # Model to use
        
        logger.info(f"Initialized Agentic Orchestrator V3 with {len(self.tools)} shared tools")
        logger.info("Using direct OpenAI API for true approval capability (can intercept before execution)")

    async def confirm_and_execute(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """
        Execute a wrapped tool - the wrapper handles approval and execution.
        The wrapped tools already handle classification internally.
        """
        tool = self.tool_map.get(tool_name)
        if not tool:
            return json.dumps({"error": f"Tool {tool_name} not found"})
        
        logger.info(f"🔔 Agent wants to call tool: {tool_name} with args: {tool_args}")
        
        # Call the wrapped tool - it handles approval logic internally
        try:
            result = await tool(**tool_args)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            result = json.dumps({"status": "error", "error": str(e)})
        
        # Parse result to check if approval is needed
        try:
            if isinstance(result, str):
                result_dict = json.loads(result)
                if result_dict.get("status") == "pending_approval":
                    # Tool requires approval - track it
                    action_id = self._generate_action_id()
                    
                    # Store pending action with tool reference
                    pending_action = {
                        "action_id": action_id,
                        "action_name": tool_name,
                        "parameters": tool_args,
                        "tool": tool,  # Store wrapped tool reference for later execution
                        "status": "pending_approval",
                        "type": "irreversible",
                        "queued_at": datetime.now().isoformat()
                    }
                    self.pending_actions.append(pending_action)
                    
                    # Track in database (not executed)
                    await self._track_action(
                        action_name=tool_name,
                        action_category="tool_call",
                        details=tool_args,
                        confidence=0.85,
                        executed=False
                    )
                    
                    logger.warning(f"🟠 Action {tool_name} queued for approval (ID: {action_id})")
                    
                    # Return with action_id for UI tracking
                    result_dict["action_id"] = action_id
                    return json.dumps(result_dict)
                    
                elif result_dict.get("status") == "error":
                    logger.error(f"Tool {tool_name} returned error: {result_dict.get('error')}")
                else:
                    # Tool executed successfully
                    logger.info(f"✅ Tool {tool_name} executed successfully")
                    
                    # Track successful execution
                    await self._track_action(
                        action_name=tool_name,
                        action_category="tool_call",
                        details=tool_args,
                        confidence=0.85,
                        executed=True
                    )
                    
                    # Add to auto-executed list
                    self.auto_executed_actions.append({
                        "action_name": tool_name,
                        "parameters": tool_args,
                        "status": "executed",
                        "type": "reversible"
                    })
        except json.JSONDecodeError:
            # Result is not JSON, assume success
            logger.info(f"Tool {tool_name} returned non-JSON result")
            
            # Track execution
            await self._track_action(
                action_name=tool_name,
                action_category="tool_call",
                details=tool_args,
                confidence=0.85,
                executed=True
            )
        
        return result
    
    def _get_agent_instructions(self) -> str:
        """Get comprehensive instructions for the autonomous agent"""
        return """You are an autonomous factory automation orchestrator for a garment price tag manufacturing facility.

## CRITICAL INSTRUCTION: ALWAYS CALL classify_email_intent FIRST!

Before doing ANYTHING else, you MUST first call classify_email_intent to understand what type of email this is.
This is MANDATORY - do not skip this step or call any other tool before this one.

## YOUR AVAILABLE TOOLS

You have exactly these tools available (USE IN ORDER):
1. **classify_email_intent** - Classify email type (ORDER/PAYMENT/INQUIRY/etc.) - ⚠️ MUST BE CALLED FIRST!
2. **check_emails** - Check for new emails
3. **send_email_response** - Send email response (IRREVERSIBLE - requires approval)
4. **search_inventory** - Search for items in inventory by query
5. **process_complete_order** - Process order with attachments and search
6. **update_order_status** - Update order status in database
7. **extract_excel_data** - Extract data from Excel attachments
8. **extract_pdf_data** - Extract text from PDF attachments
9. **process_tag_image** - Process tag images with AI
10. **generate_document** - Generate quotations/invoices
11. **get_customer_context** - Get customer history
12. **track_payment** - Track payment confirmations
13. **handle_supplier_inquiry** - Handle supplier communications

## WORKFLOW FOR PROCESSING EMAILS

### Step 1: ALWAYS Classify First
Use `classify_email_intent` with ALL parameters:
- email_subject: The email subject
- email_body: The email body text
- sender_email: Who sent it
- recipient_email: Who received it

### Step 2: Based on Classification, Take Action

For NEW_ORDER:
1. Use `process_complete_order` to handle the order
2. Use `search_inventory` to find matching items
3. Use `generate_document` for proforma invoice (requires approval)
4. Use `send_email_response` if response needed (requires approval)

For PAYMENT:
1. Use `track_payment` to process payment info
2. Use `update_order_status` to update database
3. Use `send_email_response` if confirmation needed (requires approval)

For INQUIRY:
1. Use `search_inventory` for product inquiries
2. Use `get_customer_context` for customer info
3. Use `send_email_response` to reply (requires approval)

For SUPPLIER:
1. Use `handle_supplier_inquiry` for vendor communications

### Step 3: Handle Attachments
- Use `extract_excel_data` for .xlsx/.xls/.csv files
- Use `extract_pdf_data` for .pdf files
- Use `process_tag_image` for image files

## TWO-TIER ACTION SYSTEM

### Reversible Actions (Auto-Execute):
- classify_email_intent
- check_emails
- search_inventory
- extract_excel_data
- extract_pdf_data
- get_customer_context
- update_order_status

### Irreversible Actions (Require Approval):
- send_email_response
- generate_document
- process_complete_order (when it modifies data)
- track_payment (when confirming payment)

## IMPORTANT RULES
1. ALWAYS call `classify_email_intent` first
2. Only use tools from the available list above
3. Don't call tools that don't exist
4. Some emails don't need responses - be intelligent
5. When sending emails or generating documents, they require approval"""

    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an email using direct API with true approval capability"""
        logger.info(f"Processing email: {email_data.get('subject', 'No subject')}")
        
        # Phase 3: Generate workflow ID for this email processing
        self.current_workflow_id = self._generate_workflow_id()
        self.workflow_actions = []  # Reset actions for new workflow
        logger.info(f"Starting workflow {self.current_workflow_id}")
        
        # Phase 4: Set workflow ID in two-tier executor
        self.two_tier_executor.set_workflow_id(self.current_workflow_id)

        # Create trace name based on email
        trace_name = f"Email_Processing_{email_data.get('subject', 'No_subject')[:30]}"

        # Process without SDK trace (we'll add our own monitoring)
        # with trace(trace_name):  # SDK trace not available with direct API
        try:
            # Prepare attachments if present
            attachments_data = []
            attachment_summary = []
            if email_data.get("attachments"):
                logger.info(
                    f"Processing {len(email_data['attachments'])} attachments"
                )
                for attachment in email_data["attachments"]:
                    # Log attachment details
                    logger.debug(f"Attachment: {attachment}")

                    # Store attachment data with file paths
                    att_data = {
                        "filename": attachment.get("filename", "unknown"),
                        "filepath": attachment.get(
                            "filepath", ""
                        ),  # File path instead of content
                        "mime_type": attachment.get(
                            "mime_type", "application/octet-stream"
                        ),
                    }
                    attachments_data.append(att_data)

                    # Log if filepath is missing
                    if not att_data["filepath"]:
                        logger.warning(
                            f"Missing filepath for attachment: {att_data['filename']}"
                        )

                    # Create summary for prompt
                    attachment_summary.append(
                        f"{attachment.get('filename', 'unknown')} ({attachment.get('mime_type', 'unknown')})"
                    )

                logger.info(
                    f"Prepared {len(attachments_data)} attachments for processing"
                )

            # Store attachments in context for tools to access
            # Need to pass this to the order tools
            if hasattr(self.tool_factory, 'order_processor'):
                # We need a way to set context - for now, use the global approach
                # This is a limitation that needs addressing in production
                pass

            # Construct prompt for autonomous processing with classification
            email_body = email_data.get("body", "No body")
            recipient_email = email_data.get(
                "to",
                (
                    self.primary_emails[0]
                    if self.primary_emails
                    else "orders@factory.com"
                ),
            )

            # Format attachment list for AI
            attachment_list = ""
            if attachments_data:
                attachment_list = "\n\nAttachment Details:"
                for att in attachments_data:
                    attachment_list += f"\n- {att['filename']} (path: {att['filepath']})"
            
            prompt = f"""
Process this email using the available tools.

Email Details:
- From: {email_data.get('from', 'Unknown')}
- To: {recipient_email}
- Subject: {email_data.get('subject', 'No subject')}
- Body: {email_body}
- Attachments: {len(attachments_data)} files{attachment_list}

REQUIRED STEPS:

1. FIRST: Call `classify_email_intent` with these parameters:
   - email_subject: "{email_data.get('subject', 'No subject')}"
   - email_body: "{email_body[:500]}"
   - sender_email: "{email_data.get('from', 'Unknown')}"
   - recipient_email: "{recipient_email}"

2. THEN based on the classification result:
   
   If NEW_ORDER or order details found:
   - Call `process_complete_order` with the email_data and attachments list
   - For PDF attachments, call `extract_pdf_data` with filename parameter from the paths above
   - For Excel attachments, call `extract_excel_data` with filename parameter from the paths above
   - Call `search_inventory` for any specific items mentioned (like "TBALWBL0009N")
   
   If PAYMENT mentioned:
   - Call `track_payment` with payment details
   - Call `update_order_status` if order ID is known
   
   If INQUIRY:
   - Call `search_inventory` with the query
   - Call `get_customer_context` for customer info

3. FINALLY: If a response is truly needed (not all emails need responses):
   - Call `send_email_response` with appropriate message

IMPORTANT TOOL PARAMETERS:
- extract_pdf_data needs: filename (use the full path from attachment list)
- extract_excel_data needs: filename (use the full path from attachment list)
- search_inventory needs: query (text to search for)
- process_complete_order needs: email_data and attachments

REMEMBER:
- Only use tools from the available list
- Use the file paths provided above for attachment processing
- Some emails are just FYI and don't need responses
- Irreversible actions will be queued for approval
"""

            # Start monitoring this trace
            trace_monitor.start_trace(
                trace_name,
                {
                    "email_from": email_data.get("from", "Unknown"),
                    "email_subject": email_data.get("subject", "No subject"),
                    "email_type": email_data.get("email_type", "unknown"),
                },
            )

            # Use direct OpenAI API for true approval capability
            messages = [
                {"role": "system", "content": self.agent_instructions},
                {"role": "user", "content": prompt}
            ]
            
            # Log the tool schemas being passed
            logger.debug(f"Passing {len(self.tool_schemas)} tool schemas to OpenAI")
            for schema in self.tool_schemas[:3]:  # Log first 3 schemas
                logger.debug(f"Tool schema: {schema.get('function', {}).get('name', 'unknown')}")
            
            # Get initial response from model with tool schemas
            logger.info("Calling OpenAI API with tools...")
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self.tool_schemas,
                tool_choice="auto"
            )
            
            # Log the raw response
            logger.debug(f"OpenAI response received: {response.choices[0].message}")

            # Reset validator for new email
            self.validator.reset()
            
            # Determine validation context
            validation_context = {
                "has_attachments": bool(email_data.get("attachments")),
                "email_data": email_data
            }
            
            # Process tool calls with TRUE approval capability AND validation
            tool_calls = []
            auto_executed = []
            pending_approval = []
            
            # Tool calling loop with validation
            max_iterations = 10
            iteration = 0
            validation_failures = 0
            max_validation_failures = 3
            result = None
            
            # Continue processing until no more tools needed or max iterations
            while iteration < max_iterations:
                # Make API call with tools (allow continued iteration)
                if iteration > 0:
                    logger.info(f"Tool calling iteration {iteration} - allowing AI to continue...")
                    response = await self.openai_client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=self.tool_schemas,
                        tool_choice="auto"
                    )
                
                # Check if AI wants to make tool calls
                if not response.choices[0].message.tool_calls:
                    # No more tools needed - get final response
                    result = response.choices[0].message.content
                    logger.info("AI completed tool calling - no more tools needed")
                    break
                
                # Process tool calls
                logger.info(f"AI requested {len(response.choices[0].message.tool_calls)} tool calls in iteration {iteration}")
                tool_results = []
                had_validation_failure = False
                
                for tool_call in response.choices[0].message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)
                    logger.info(f"Tool call requested: {tool_name} with args: {tool_args}")
                    
                    # VALIDATE BEFORE EXECUTION
                    is_valid, feedback = self.validator.validate(
                        tool_name,
                        tool_args,
                        validation_context
                    )
                    
                    if is_valid:
                        # Validation passed - execute the tool
                        logger.info(f"✅ Validation passed for: {tool_name}")
                        
                        # THIS IS THE KEY: Intercept and apply approval logic BEFORE execution
                        result = await self.confirm_and_execute(tool_name, tool_args)
                        
                        # Record successful execution
                        self.validator.record(tool_name, result)
                    
                        # Parse result to track what happened
                        try:
                            result_dict = json.loads(result) if isinstance(result, str) else result
                            if isinstance(result_dict, dict) and result_dict.get("status") == "pending_approval":
                                # Action was queued for approval (NOT executed)
                                pending_approval.append({
                                    "action_id": result_dict.get("action_id"),
                                    "action_name": tool_name,
                                    "type": "irreversible",
                                    "status": "pending_approval"
                                })
                            else:
                                # Action was auto-executed (reversible)
                                auto_executed.append({
                                    "action_name": tool_name,
                                    "type": "reversible",
                                    "status": "executed"
                                })
                        except:
                            # If we can't parse, assume it was executed
                            auto_executed.append({
                                "action_name": tool_name,
                                "type": "unknown",
                                "status": "executed"
                            })
                        
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "result": str(result)
                        })
                    
                    else:
                        # Validation failed - send error back to AI
                        logger.warning(f"❌ Validation failed for {tool_name}: {feedback}")
                        had_validation_failure = True
                        validation_failures += 1
                        
                        # Create detailed error response
                        error_response = {
                            "error": "validation_failed",
                            "tool": tool_name,
                            "message": feedback,
                            "suggestions": self.validator.get_suggested_next_tools(),
                            "executed_so_far": self.validator.execution_history,
                            "guidance": (
                                "IMPORTANT: Your tool call was invalid. Please read the error message carefully. "
                                "You must follow the correct workflow order. "
                                "Always call 'classify_email_intent' first if you haven't already."
                            )
                        }
                        
                        # Add error result
                        tool_results.append({
                            "tool_call_id": tool_call.id,
                            "result": json.dumps(error_response)
                        })
                    
                    # Track tool call
                    tool_calls.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": str(result)[:200]  # Truncate for logging
                    })
                    
                    # Add to trace monitor
                    trace_monitor.add_tool_call(
                        tool_name=tool_name,
                        args=tool_args,
                        result=str(result)[:200]
                    )
                    
                    logger.debug(f"Processed tool call: {tool_name} with result: {str(result)[:100]}")
                
                # Add results to message history
                messages.append(response.choices[0].message)
                for tool_result in tool_results:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_result["tool_call_id"],
                        "content": tool_result["result"]
                    })
                
                # If validation failed, add strong guidance
                if had_validation_failure:
                    suggestions = self.validator.get_suggested_next_tools()
                    executed = self.validator.execution_history
                    
                    # Build guidance message
                    guidance_msg = (
                        "⚠️ VALIDATION FAILED - PLEASE FOLLOW THE CORRECT WORKFLOW:\n\n"
                    )
                    
                    if not executed:
                        guidance_msg += (
                            "You haven't executed any valid tools yet.\n"
                            "YOU MUST START WITH: classify_email_intent\n\n"
                            "Call it with these parameters:\n"
                            "- email_subject: The subject of the email\n"
                            "- email_body: The body of the email\n"
                            "- sender_email: The sender's email address\n"
                        )
                    else:
                        guidance_msg += (
                            f"Tools executed so far: {executed}\n"
                            f"Suggested next tools: {suggestions}\n\n"
                            "Remember the correct order:\n"
                            "1. classify_email_intent (MUST be first)\n"
                            "2. extract attachments (if any)\n"
                            "3. process the order\n"
                            "4. generate response"
                        )
                    
                    # Add system message with guidance
                    messages.append({
                        "role": "system",
                        "content": guidance_msg
                    })
                    
                    # Check if too many validation failures
                    if validation_failures >= max_validation_failures:
                        logger.error(f"Too many validation failures ({validation_failures})")
                        result = (
                            "Workflow terminated due to repeated validation failures. "
                            "Please ensure you call 'classify_email_intent' first."
                        )
                        break
                
                iteration += 1
            
            # Check if we hit max iterations
            if iteration >= max_iterations and result is None:
                logger.warning(f"Hit maximum iterations ({max_iterations})")
                result = "Maximum iterations reached. Workflow may be incomplete."

            # Log trace information
            logger.info(f"Trace created: {trace_name}")
            logger.info(f"Tool calls made: {len(tool_calls)}")

            # End trace with summary
            final_output = str(result) if result else "No output"
            trace_monitor.end_trace("completed", final_output[:200])

            # Phase 3: Generate reasoning for actions taken
            reasoning = self._generate_reasoning(email_data, self.workflow_actions)
            
            # Phase 4: Get two-tier execution summary (currently not used as tools execute directly)
            # workflow_summary = self.two_tier_executor.get_workflow_summary()
            
            # Sync pending actions to Human Review system
            if pending_approval and hasattr(self, 'human_manager'):
                logger.info(f"Syncing {len(pending_approval)} pending actions to Human Review system")
                for action in pending_approval:
                    try:
                        # Create a review request for each pending action
                        review_request = await self.human_manager.create_review_request(
                            order_id=None,  # We don't have order IDs for these actions
                            customer_email=email_data.get("from", "unknown@email.com"),
                            order_details={
                                "action": action.get("action_name"),
                                "parameters": action.get("parameters", {}),
                                "action_id": action.get("action_id"),
                                "workflow_id": self.current_workflow_id,
                            },
                            confidence_score=0.75,  # Default confidence for approval items
                            reason=f"Irreversible action requires approval: {action.get('action_name')}",
                            priority="MEDIUM",
                            context={
                                "email_subject": email_data.get("subject", ""),
                                "email_body": email_data.get("body", "")[:500],
                                "action_type": "irreversible",
                            }
                        )
                        logger.info(f"Created review request {review_request['request_id']} for {action.get('action_name')}")
                    except Exception as e:
                        logger.error(f"Failed to create review request for action {action.get('action_name')}: {e}")
            
            # Get workflow summary from validator
            workflow_summary = self.validator.get_workflow_summary()
            
            # Log validation statistics
            logger.info(f"Validation stats: {workflow_summary['validation_stats']}")
            logger.info(f"Workflow complete: {workflow_summary['is_complete']}")
            
            # Build result
            result_dict = {
                "success": True,
                "email_id": email_data.get("message_id", "unknown"),
                "processing_complete": True,
                "trace_name": trace_name,
                "workflow_id": self.current_workflow_id,  # Add workflow ID
                "tool_calls": tool_calls,
                "actions_tracked": len(self.workflow_actions),  # Number of tracked actions
                "decisions_made": [],
                "documents_generated": [],
                "final_summary": str(result),
                "reasoning": reasoning,  # Add reasoning
                "autonomous_actions": len(tool_calls),
                # Validation statistics
                "validation_stats": workflow_summary["validation_stats"],
                "workflow_complete": workflow_summary["is_complete"],
                "executed_tools": workflow_summary["executed_tools"],
                "email_type": workflow_summary.get("email_type", "unknown"),
                # Phase 4: Two-tier execution results
                # Using our tracked lists instead of two_tier_executor (which isn't being used currently)
                "auto_executed_actions": auto_executed,
                "pending_approval_actions": pending_approval,
            }

            return result_dict

        except Exception as e:
            logger.error(f"Error in autonomous processing: {e}")
            trace_monitor.end_trace("failed", str(e))
            return {
                "success": False,
                "email_id": email_data.get("message_id", "unknown"),
                "error": str(e),
                "trace_name": trace_name,
            }

    async def start_email_monitoring(self):
        """Start autonomous email monitoring with tracing"""
        # Skip monitoring if no Gmail agent
        if not self.gmail_agent:
            logger.info("Email monitoring disabled - no Gmail agent configured")
            return

        self.is_monitoring = True
        logger.info("Starting autonomous email monitoring...")

        cycle_count = 0
        while self.is_monitoring:
            cycle_count += 1
            trace_name = f"Email_Monitoring_Cycle_{cycle_count}"

            # Process without SDK trace
            try:
                # Let the agent check for emails autonomously
                check_prompt = """
Check for new emails and process any that you find.
Use your tools to:
1. Check for new emails
2. Process each email completely
3. Take all necessary actions
4. Provide a summary of what was done
"""

                # Use direct API for monitoring
                messages = [
                    {"role": "system", "content": self.agent_instructions},
                    {"role": "user", "content": check_prompt}
                ]
                
                result = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=self.tool_schemas,
                    tool_choice="auto"
                )

                # Log monitoring results
                tool_count = len(result.choices[0].message.tool_calls) if result.choices[0].message.tool_calls else 0
                logger.info(
                    f"Monitoring cycle {cycle_count} complete. Actions taken: {tool_count}"
                )
                logger.info(f"Trace: {trace_name}")

                # Wait before next cycle
                await asyncio.sleep(settings.email_poll_interval)

            except Exception as e:
                logger.error(f"Error in monitoring cycle {cycle_count}: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def stop(self):
        """Stop the orchestrator"""
        self.is_monitoring = False
        logger.info("Autonomous orchestrator stopped")
    
    def is_running(self) -> bool:
        """Check if orchestrator is running"""
        return self.is_monitoring
    
    async def approve_action(self, action_id: str) -> Dict[str, Any]:
        """
        Approve and execute a pending irreversible action.
        Uses the original tool via ToolContext to bypass approval check.
        
        Args:
            action_id: ID of the action to approve
            
        Returns:
            Result of executing the action
        """
        # Find the pending action
        pending_action = None
        for action in self.pending_actions:
            if action.get("action_id") == action_id:
                pending_action = action
                break
        
        if not pending_action:
            return {"error": f"Action {action_id} not found in pending actions"}
        
        logger.info(f"✅ APPROVING ACTION: {pending_action['action_name']} ({action_id})")
        
        # Get the wrapped tool from the pending action
        wrapped_tool = pending_action.get("tool")
        if not wrapped_tool:
            # Fallback to tool map if not stored
            wrapped_tool = self.tool_map.get(pending_action['action_name'])
        
        if not wrapped_tool or not hasattr(wrapped_tool, 'original_tool'):
            return {"error": f"Tool not found or not properly wrapped for {pending_action['action_name']}"}
        
        # Get the original tool to bypass approval logic
        original_tool = wrapped_tool.original_tool
        params = pending_action.get('parameters', {})
        
        try:
            # Execute the original tool directly with proper ToolContext
            from agents.tool_context import ToolContext
            from agents.usage import Usage
            
            # Convert params to JSON string for on_invoke_tool
            input_json = json.dumps(params)
            
            # Create ToolContext for approved execution
            ctx = ToolContext(
                context=None,  # Can be enhanced with session context
                usage=Usage(),
                tool_name=pending_action['action_name'],
                tool_call_id=f"approved_{action_id}"
            )
            
            # Execute the tool
            result = await original_tool.on_invoke_tool(ctx, input_json)
            
            # Update action status
            pending_action['status'] = 'approved_and_executed'
            pending_action['executed_at'] = datetime.now().isoformat()
            pending_action['result'] = result
            
            # Track in database
            await self._track_action(
                action_name=pending_action['action_name'],
                action_type="irreversible",
                parameters=params,
                result=result,
                executed=True
            )
            
            # Remove from pending list
            self.pending_actions.remove(pending_action)
            
            logger.info(f"✅ Successfully executed approved action: {pending_action['action_name']}")
            
            return {
                "status": "success",
                "action_id": action_id,
                "action_name": pending_action['action_name'],
                "result": result
            }
            
        except Exception as e:
            logger.error(f"Error executing approved action {action_id}: {e}")
            return {
                "status": "error",
                "action_id": action_id,
                "error": str(e)
            }
    
    async def reject_action(self, action_id: str, reason: str = "") -> Dict[str, Any]:
        """
        Reject a pending action.
        
        Args:
            action_id: ID of the action to reject
            reason: Optional reason for rejection
            
        Returns:
            Confirmation of rejection
        """
        # Find and remove the pending action
        for action in self.pending_actions:
            if action.get("action_id") == action_id:
                self.pending_actions.remove(action)
                
                logger.info(f"❌ REJECTED ACTION: {action['action_name']} ({action_id})")
                
                # Track rejection in database
                await self._track_action(
                    action_name=action['action_name'],
                    action_type="irreversible",
                    parameters=action.get('parameters', {}),
                    result={"status": "rejected", "reason": reason},
                    executed=False
                )
                
                return {
                    "status": "rejected",
                    "action_id": action_id,
                    "action_name": action['action_name'],
                    "reason": reason
                }
        
        return {"error": f"Action {action_id} not found in pending actions"}
    
    def get_pending_actions(self) -> List[Dict[str, Any]]:
        """Get list of all pending actions awaiting approval"""
        return self.pending_actions.copy()
    
    def _wrap_tools_with_two_tier(self):
        """
        Prepare tools for two-tier execution logic.
        Phase 4 - Since we can't wrap tools without schema issues, we track execution in process_email.
        
        Returns:
            List of original tools (interception happens at runtime)
        """
        # Build a map of tool names to functions for approval execution
        self.tool_map = {}
        for tool in self.tools:
            tool_name = tool.name
            # The tool itself IS callable - @function_tool decorated functions remain callable!
            # No need to extract anything - the FunctionTool object is what we call
            self.tool_map[tool_name] = tool
            
            # Classify each tool for later reference
            action_type = self.action_classifier.classify_action(tool_name)
            if action_type == ActionType.IRREVERSIBLE:
                logger.info(f"  🟠 {tool_name} - REQUIRES APPROVAL")
            else:
                logger.info(f"  🟢 {tool_name} - AUTO-EXECUTE")
        
        logger.info(f"Prepared {len(self.tools)} tools for two-tier execution")
        logger.info("Approval logic will be applied at runtime during tool call extraction")
        
        # Return original tools - we'll intercept execution in process_email
        return self.tools
    
    def _generate_workflow_id(self) -> str:
        """Generate a unique workflow ID"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        return f"WF-{timestamp}-{unique_id}"
    
    def _generate_action_id(self) -> str:
        """Generate a unique action ID"""
        return f"ACT-{uuid.uuid4().hex[:12]}"
    
    async def _track_action(
        self,
        action_name: str,
        action_category: str,
        details: Dict[str, Any],
        confidence: float = 0.0,
        order_id: Optional[str] = None,
        executed: bool = True,
        action_type: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        result: Optional[Any] = None
    ) -> str:
        """
        Track an action in the audit log.
        Phase 3 - Action tracking for audit trail.
        
        Args:
            action_name: Name of the action/tool
            action_category: Category of action
            details: Action details
            confidence: Confidence score
            order_id: Optional order ID
            
        Returns:
            Action ID
        """
        action_id = self._generate_action_id()
        
        # Classify the action
        action_type = self.action_classifier.classify_action(action_name)
        
        # Generate reasoning (simplified for now)
        reasoning = f"Executing {action_name} as part of workflow {self.current_workflow_id}"
        
        try:
            with get_db() as db:
                # Create audit record
                audit = ActionAudit(
                    action_id=action_id,
                    workflow_id=self.current_workflow_id or self._generate_workflow_id(),
                    order_id=order_id,
                    action_type=action_type.value,
                    action_category=action_category,
                    action_name=action_name,
                    description=f"Tool call: {action_name}",
                    details=details,
                    can_rollback=1 if action_type == ActionType.REVERSIBLE else 0,
                    executed=1 if executed else 0,  # Use the executed parameter
                    executed_at=datetime.now() if executed else None,
                    confidence=confidence,
                    reasoning=reasoning,
                    requires_approval=1 if action_type == ActionType.IRREVERSIBLE else 0,
                )
                
                db.add(audit)
                db.commit()
                
                # Track in memory
                self.workflow_actions.append({
                    "action_id": action_id,
                    "action_name": action_name,
                    "action_type": action_type.value,
                    "timestamp": datetime.now().isoformat()
                })
                
                logger.info(f"Tracked action {action_id}: {action_name} ({action_type.value})")
                
        except Exception as e:
            logger.error(f"Failed to track action in audit log: {e}")
        
        return action_id
    
    def _generate_reasoning(
        self,
        email_data: Dict[str, Any],
        actions_taken: List[Dict[str, Any]]
    ) -> str:
        """
        Generate human-readable reasoning for actions taken.
        Uses proposal engine's reasoning capabilities.
        
        Args:
            email_data: Email information
            actions_taken: List of actions executed
            
        Returns:
            Reasoning text
        """
        # Build summary of actions
        action_summary = []
        for action in actions_taken:
            action_summary.append(f"- {action.get('action_name', 'Unknown action')}")
        
        reasoning = f"""
        Processed email from {email_data.get('from', 'unknown')} 
        regarding {email_data.get('subject', 'no subject')}.
        
        Actions taken:
        {chr(10).join(action_summary)}
        
        Workflow ID: {self.current_workflow_id}
        """
        
        return reasoning.strip()

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics for monitoring"""
        if hasattr(self, 'validator'):
            return self.validator.get_workflow_summary()
        return {}
    
    async def learn_from_feedback(
        self, email_id: str, actual_intent: str, was_correct: bool
    ):
        """Update patterns based on human feedback"""
        try:
            from ..factory_database.connection import get_db
            from ..factory_database.models import EmailPattern

            with get_db() as db:
                # Find the pattern that was used
                pattern = (
                    db.query(EmailPattern).filter_by(intent_type=actual_intent).first()
                )

                if pattern:
                    if was_correct:
                        pattern.auto_approved_count += 1
                        pattern.confidence = min(0.98, pattern.confidence + 0.02)
                    else:
                        pattern.manual_review_count += 1
                        pattern.confidence = max(0.3, pattern.confidence - 0.1)

                    db.commit()
                    logger.info(
                        f"Learned from feedback: {actual_intent} correct={was_correct}"
                    )
        except Exception as e:
            logger.error(f"Failed to learn from feedback: {e}")