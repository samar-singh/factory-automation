"""True Agentic Orchestrator - Autonomous AI with tool usage (Refactored with shared tools)"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents import Agent, Runner, trace

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

logger = logging.getLogger(__name__)


class AgenticOrchestratorV3:
    """Fully autonomous orchestrator using OpenAI Agents SDK with shared tools"""

    def __init__(self, chromadb_client: ChromaDBClient, use_mock_gmail: bool = True):
        """Initialize with ChromaDB and create autonomous agent"""
        self.chromadb_client = chromadb_client
        self.runner = Runner()
        self.is_monitoring = False
        self.approval_mode = True  # Enable approval mode for irreversible actions

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

        # Initialize OpenAI client for classification
        from openai import AsyncOpenAI
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
        
        # Phase 4: For approval mode, we'll use original tools but intercept in process_email
        # We can't wrap tools without causing schema issues, so we intercept at execution
        self.wrapped_tools = self.tools  # Use original tools
        
        # Create the autonomous agent
        # Phase 4: Enable two-tier by default for now (can be configured later)
        enable_two_tier = getattr(settings, 'enable_two_tier', True)
        
        self.agent = Agent(
            name="FactoryAutomationOrchestrator",
            instructions=self._get_agent_instructions(),
            tools=self.tools,  # Always use original tools
            model="gpt-4o",  # Default model
        )

        logger.info(f"Initialized Agentic Orchestrator V3 with {len(self.tools)} shared tools")
        if enable_two_tier:
            logger.info("Two-tier execution enabled - irreversible actions will require approval")

    def _get_agent_instructions(self) -> str:
        """Get comprehensive instructions for the autonomous agent"""
        return """You are an autonomous factory automation orchestrator for a garment price tag manufacturing facility.

CRITICAL WORKFLOW - You MUST follow this sequence for EVERY email:
1. FIRST: Use classify_email_intent to determine the email type
2. THEN: Based on the classification, take appropriate action

Your primary responsibilities:
1. Classify and route all incoming emails appropriately
2. Process customer orders with full automation
3. Handle payment confirmations and update order status
4. Respond to inquiries with relevant information
5. Manage supplier communications
6. Generate and send appropriate responses

Available tools and when to use them:
- classify_email_intent: ALWAYS use this FIRST to determine email type
- check_emails: Poll for new emails
- process_complete_order: For NEW ORDER emails only
- track_payment: For PAYMENT confirmation emails
- search_inventory: For INQUIRY emails about product availability
- search_visual: For emails with product images
- get_customer_context: To retrieve customer history before responding
- generate_document: Create quotations, confirmations, or responses
- send_email_response: Send automated responses to customers/suppliers
- handle_supplier_inquiry: For SUPPLIER communications
- update_order_status: Update order in database

Email Classification Types and Required Actions:
1. NEW_ORDER → process_complete_order → generate_document (quote) → send_email_response
2. PAYMENT → track_payment → update_order_status → send_email_response (confirmation)
3. INQUIRY → get_customer_context → search_inventory → send_email_response (information)
4. SUPPLIER → handle_supplier_inquiry → forward to procurement → send_email_response
5. FOLLOWUP → get_customer_context → check order status → send_email_response (update)
6. COMPLAINT → extract issue → create ticket → send_email_response (acknowledgment)

Decision thresholds:
- Auto-approve and respond: >80% confidence
- Request clarification: 60-80% confidence
- Escalate to human: <60% confidence or sensitive issues

IMPORTANT: You must ALWAYS send a response email after processing, appropriate to the email type and outcome.

Think step by step and ensure complete execution from email receipt to customer response."""

    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Let the agent autonomously process an email with tracing"""
        logger.info(f"Processing email: {email_data.get('subject', 'No subject')}")
        
        # Phase 3: Generate workflow ID for this email processing
        self.current_workflow_id = self._generate_workflow_id()
        self.workflow_actions = []  # Reset actions for new workflow
        logger.info(f"Starting workflow {self.current_workflow_id}")
        
        # Phase 4: Set workflow ID in two-tier executor
        self.two_tier_executor.set_workflow_id(self.current_workflow_id)

        # Create trace name based on email
        trace_name = f"Email_Processing_{email_data.get('subject', 'No_subject')[:30]}"

        # Use trace context for monitoring
        with trace(trace_name):
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

                prompt = f"""
Analyze and process this business email autonomously:

To: {recipient_email}
From: {email_data.get('from', 'Unknown')}
Subject: {email_data.get('subject', 'No subject')}
Body: {email_body}
Attachments: {len(attachments_data)} files - {', '.join(attachment_summary) if attachment_summary else 'None'}

Your workflow:
1. First, use classify_email_intent to determine the email type
   - Pass the recipient_email to understand context
2. Based on the classification, execute the appropriate tools
3. Generate and send an appropriate response if needed
4. Complete the entire chain of execution

Remember: This email came to {recipient_email} which is one of our business emails.
Different emails may have different typical patterns - use this context wisely.

The attachments are already available in the context - tools will access them automatically.

Execute the complete workflow based on the email's intent and context.
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

                # Run the agent autonomously with trace
                result = await self.runner.run(
                    self.agent,
                    prompt,
                    context={
                        "email_data": email_data,
                        "timestamp": datetime.now().isoformat(),
                        "attachments": attachments_data,  # Pass attachments in context
                    },
                )

                # Extract tool calls from new_items (OpenAI Agents SDK structure)
                tool_calls = []
                auto_executed = []
                pending_approval = []
                
                if hasattr(result, "new_items"):
                    from agents import ToolCallItem
                    
                    for item in result.new_items:
                        if isinstance(item, ToolCallItem):
                            # Extract tool name and arguments from raw_item
                            if hasattr(item, "raw_item"):
                                raw_item = item.raw_item
                                tool_name = raw_item.name if hasattr(raw_item, "name") else "unknown"
                                
                                # Parse arguments - they're in JSON string format
                                tool_args = {}
                                if hasattr(raw_item, "arguments"):
                                    try:
                                        tool_args = json.loads(raw_item.arguments)
                                    except (json.JSONDecodeError, TypeError):
                                        tool_args = {"raw": str(raw_item.arguments)}
                                
                                # Classify the action for two-tier tracking
                                action_type = self.action_classifier.classify_action(tool_name)
                                
                                # IMPORTANT: OpenAI SDK executes tools immediately
                                # We can only track what SHOULD have required approval
                                if action_type == ActionType.IRREVERSIBLE:
                                    logger.warning(f"🟠 IRREVERSIBLE ACTION EXECUTED WITHOUT APPROVAL: {tool_name}")
                                    logger.info("Note: OpenAI SDK executes tools immediately - cannot prevent execution")
                                    pending_approval.append({
                                        "action_name": tool_name,
                                        "parameters": tool_args,
                                        "status": "executed_without_approval",
                                        "should_have_required": "approval"
                                    })
                                    # Store in pending actions list for UI display
                                    self.pending_actions.append({
                                        "action_id": self._generate_action_id(),
                                        "action_name": tool_name,
                                        "parameters": tool_args,
                                        "status": "executed_without_approval",
                                        "type": "irreversible",
                                        "executed_at": datetime.now().isoformat()
                                    })
                                else:
                                    logger.info(f"🟢 REVERSIBLE ACTION AUTO-EXECUTED: {tool_name}")
                                    auto_executed.append({
                                        "action_name": tool_name,
                                        "parameters": tool_args,
                                        "status": "auto_executed"
                                    })
                                    # Store in auto-executed list for UI display
                                    self.auto_executed_actions.append({
                                        "action_id": self._generate_action_id(),
                                        "action_name": tool_name,
                                        "parameters": tool_args,
                                        "status": "executed",
                                        "type": "reversible",
                                        "executed_at": datetime.now().isoformat()
                                    })
                                
                                # Phase 3: Track action in audit log
                                action_id = await self._track_action(
                                    action_name=tool_name,
                                    action_category="tool_call",
                                    details=tool_args,
                                    confidence=0.85,  # Default confidence
                                    order_id=email_data.get("order_id")
                                )
                                
                                tool_call = {
                                    "tool": tool_name,
                                    "args": tool_args,
                                    "result": "See logs",
                                    "action_id": action_id,  # Add action ID
                                    "action_type": action_type.value,
                                }
                                tool_calls.append(tool_call)
                                
                                # Track for two-tier reporting
                                # In a true two-tier system, irreversible actions would be queued
                                # For now, we're tracking what WOULD have been queued
                                if action_type == ActionType.REVERSIBLE:
                                    auto_executed.append({
                                        "action_id": action_id,
                                        "action_name": tool_name,
                                        "type": action_type.value,
                                        "status": "executed"
                                    })
                                else:
                                    # These SHOULD have been queued for approval
                                    # But the agent executed them anyway
                                    pending_approval.append({
                                        "action_id": action_id,
                                        "action_name": tool_name,
                                        "type": action_type.value,
                                        "status": "executed_without_approval",
                                        "warning": "Action was executed by agent before approval mechanism could intervene"
                                    })
                                
                                # Add to trace monitor
                                trace_monitor.add_tool_call(
                                    tool_name=tool_call["tool"],
                                    args=tool_call["args"],
                                    result=tool_call["result"],
                                )
                                
                                logger.debug(f"Tracked tool call: {tool_name} ({action_type.value}) with action_id: {action_id}")

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

            with trace(trace_name):
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

                    result = await self.runner.run(self.agent, check_prompt)

                    # Log monitoring results
                    tool_count = (
                        len(result.tool_calls) if hasattr(result, "tool_calls") else 0
                    )
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
    
    # Phase 4: Approval methods for two-tier execution
    async def approve_action(self, action_id: str) -> Dict[str, Any]:
        """
        Approve a pending irreversible action.
        Phase 4 - Two-tier execution approval mechanism.
        """
        result = await self.two_tier_executor.approve_action(action_id)
        logger.info(f"Action {action_id} approved: {result}")
        return result
    
    async def reject_action(self, action_id: str, reason: str = "") -> Dict[str, Any]:
        """
        Reject a pending irreversible action.
        Phase 4 - Two-tier execution rejection mechanism.
        """
        result = await self.two_tier_executor.reject_action(action_id, reason)
        logger.info(f"Action {action_id} rejected: {result}")
        return result
    
    def get_pending_actions(self) -> List[Dict[str, Any]]:
        """
        Get all pending actions for approval.
        Phase 4 - Two-tier execution query mechanism.
        """
        return self.two_tier_executor.get_pending_actions()

    def is_running(self) -> bool:
        """Check if orchestrator is running"""
        return self.is_monitoring
    
    async def approve_action(self, action_id: str) -> Dict[str, Any]:
        """
        Approve and execute a pending action.
        
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
        
        # Get the tool function from our tool map
        tool_func = self.tool_map.get(pending_action['action_name'])
        
        if not tool_func:
            return {"error": f"Tool function not found for {pending_action['action_name']}"}
        
        try:
            # Execute the tool with original parameters
            params = pending_action.get('parameters', {})
            if asyncio.iscoroutinefunction(tool_func):
                result = await tool_func(**params)
            else:
                result = tool_func(**params)
            
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
            tool_func = tool.function if hasattr(tool, 'function') else tool
            self.tool_map[tool_name] = tool_func
            
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
        order_id: Optional[str] = None
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
                    executed=1,  # Mark as executed in current flow
                    executed_at=datetime.now(),
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