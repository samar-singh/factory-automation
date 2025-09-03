"""Proposal-Based Orchestrator - Generates workflows for human approval (Refactored with shared tools)"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents import Agent, Runner, function_tool, trace

from ..factory_config.settings import settings
from ..factory_utils.trace_monitor import trace_monitor
from ..factory_database.vector_db import ChromaDBClient
from ..factory_rag.embeddings_config import EmbeddingsManager
from ..factory_models import (
    ProposedWorkflow,
    ApprovalStatus,
)
from .proposal_engine import ProposalEngine
from .mock_gmail_agent import MockGmailAgent
from .order_processor_agent import OrderProcessorAgent
from .image_processor_agent import ImageProcessorAgent
from .tools.tool_factory import ToolFactory

logger = logging.getLogger(__name__)


class ProposalOrchestratorV4:
    """Orchestrator that generates workflow proposals using shared tools"""

    def __init__(self, chromadb_client: ChromaDBClient, use_mock_gmail: bool = True):
        """Initialize with ChromaDB and create proposal-generating agent"""
        self.chromadb_client = chromadb_client
        self.runner = Runner()
        self.is_monitoring = False
        
        # Initialize embeddings manager for Stella embeddings
        self.embeddings_manager = EmbeddingsManager(model_name="stella-400m")
        
        # Initialize proposal engine
        self.proposal_engine = ProposalEngine()
        
        # Store generated proposals
        self.proposals: List[ProposedWorkflow] = []
        
        # Load business email configuration
        self.business_emails = settings.config.get("business_emails", {})
        self.email_configs = {}
        
        # Process email configurations
        for email_config in self.business_emails.get("emails", []):
            address = email_config.get("address")
            if address:
                self.email_configs[address.lower()] = {
                    "description": email_config.get("description", ""),
                    "likely_intents": email_config.get("likely_intents", []),
                    "confidence_boost": email_config.get("confidence_boost", 0.0),
                }
        
        self.primary_emails = list(self.email_configs.keys())
        
        # Pattern learning config
        self.pattern_config = self.business_emails.get(
            "pattern_learning",
            {
                "enabled": False,  # Disabled for proposal mode
                "min_count_for_pattern": 3,
                "max_confidence": 0.95,
                "initial_confidence": 0.6,
                "confidence_increment": 0.05,
            }
        )
        
        # Initialize mock Gmail for testing
        if use_mock_gmail:
            self.gmail_agent = MockGmailAgent()
        else:
            self.gmail_agent = None
            
        # Initialize processors for analysis (not execution)
        self.order_processor = OrderProcessorAgent(chromadb_client)
        self.image_processor = ImageProcessorAgent(chromadb_client)
        
        # Initialize OpenAI client for AI analysis
        from openai import AsyncOpenAI
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        
        # Track proposals generated
        self.proposal_history = []
        
        # Create tool factory with dependencies
        self.tool_factory = ToolFactory(
            mode="propose",  # V4 generates proposals
            chromadb_client=chromadb_client,
            gmail_agent=self.gmail_agent,
            openai_client=self.openai_client,
            order_processor=self.order_processor,
            image_processor=self.image_processor,
            embeddings_manager=self.embeddings_manager,
            email_configs=self.email_configs,
            pattern_config=self.pattern_config,
        )
        
        # Get proposal-oriented tools
        self.tools = self.tool_factory.get_tools_for_v4()
        
        # Add V4-specific proposal tools
        self.tools.extend(self._create_v4_specific_tools())
        
        # Create the proposal agent
        self.agent = Agent(
            name="ProposalOrchestrator",
            instructions=self._get_proposal_instructions(),
            tools=self.tools,
            model="gpt-4o",
        )
        
        logger.info(f"Initialized Proposal Orchestrator V4 with {len(self.tools)} tools (shared + specific)")
    
    def _get_proposal_instructions(self) -> str:
        """Instructions for the proposal-generating agent"""
        return """You are a workflow proposal generator for a factory automation system.
        
Your role is to ANALYZE emails and PROPOSE comprehensive workflows for human approval.
You do NOT execute actions directly - you only generate proposals.

CRITICAL RULES:
1. NEVER execute actions directly - only propose them
2. ALWAYS generate complete workflow proposals with all necessary steps
3. INCLUDE confidence scores and risk assessments in proposals
4. PROVIDE alternatives and reasoning for each proposal
5. GENERATE contextual email drafts but do NOT send them

For each email you process:
1. First use classify_email_intent to understand the email type
2. Use search_inventory_for_proposal to gather inventory data if needed
3. Use analyze_attachments_for_proposal to process any attachments
4. Use get_customer_context to add customer history
5. Generate a comprehensive proposal with all necessary actions
6. Use enrich_proposal_with_context to add business context

Remember: You are an ADVISOR, not an executor. Your proposals must be comprehensive 
enough for humans to understand and approve/modify before execution."""
    
    def _create_v4_specific_tools(self) -> List:
        """Create V4-specific proposal management tools"""
        tools = []
        
        # Generate workflow proposal tool
        @function_tool(
            name_override="generate_workflow_proposal",
            description_override="Generate a complete workflow proposal based on analyzed email data",
        )
        def generate_workflow_proposal(
            email_subject: str,
            email_body: str,
            sender_email: str,
            classification: str,
            confidence: float
        ) -> Dict[str, Any]:
            """Generate comprehensive workflow proposal"""
            try:
                # Create minimal email data
                email_data = {
                    "from": sender_email,
                    "subject": email_subject,
                    "body": email_body,
                }
                
                # Generate proposal using proposal engine
                proposal = self.proposal_engine.generate_workflow_proposal(
                    email_data=email_data,
                    order_data=None,  # Would be extracted if needed
                    inventory_matches=[],
                    customer_data={"email": sender_email, "tier": "unknown"}
                )
                
                # Store proposal
                self.proposals.append(proposal)
                
                return {
                    "success": True,
                    "workflow_id": proposal.workflow_id,
                    "workflow_type": proposal.workflow_type.value,
                    "confidence": proposal.confidence,
                    "actions_count": len(proposal.proposed_actions),
                    "reasoning": proposal.reasoning,
                }
                
            except Exception as e:
                logger.error(f"Error generating proposal: {e}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
        tools.append(generate_workflow_proposal)
        
        # Enrich proposal with context
        @function_tool(
            name_override="enrich_proposal_with_context",
            description_override="Enrich proposal with customer history and business context",
        )
        def enrich_proposal_with_context(
            workflow_id: str,
            customer_email: str
        ) -> Dict[str, Any]:
            """Add historical context to proposal"""
            
            # Find the proposal
            proposal = None
            for p in self.proposals:
                if p.workflow_id == workflow_id:
                    proposal = p
                    break
            
            if not proposal:
                return {
                    "success": False,
                    "error": "Proposal not found"
                }
            
            # Add context (would query database in production)
            context = {
                "customer_tier": "regular" if "@gmail.com" in customer_email else "new",
                "previous_orders": 3 if "@gmail.com" in customer_email else 0,
                "payment_history": "excellent" if "@gmail.com" in customer_email else "unknown",
            }
            
            # Update proposal reasoning
            proposal.reasoning += f" Customer has {context['previous_orders']} previous orders."
            
            return {
                "success": True,
                "workflow_id": workflow_id,
                "context_added": context,
            }
        
        tools.append(enrich_proposal_with_context)
        
        # Get proposal details
        @function_tool(
            name_override="get_proposal_details",
            description_override="Get detailed information about a generated proposal",
        )
        def get_proposal_details(workflow_id: str) -> Dict[str, Any]:
            """Retrieve full proposal details"""
            
            for proposal in self.proposals:
                if proposal.workflow_id == workflow_id:
                    return {
                        "success": True,
                        "workflow_id": proposal.workflow_id,
                        "workflow_type": proposal.workflow_type.value,
                        "confidence": proposal.confidence,
                        "customer_tier": proposal.customer_tier.value,
                        "actions": [
                            {
                                "step": action.step,
                                "action": action.action.value,
                                "details": action.details,
                                "confidence": action.confidence,
                            }
                            for action in proposal.proposed_actions
                        ],
                        "reasoning": proposal.reasoning,
                    }
            
            return {
                "success": False,
                "error": "Proposal not found"
            }
        
        tools.append(get_proposal_details)
        
        # List proposals
        @function_tool(
            name_override="list_proposals",
            description_override="List all generated proposals in the current session",
        )
        def list_proposals() -> Dict[str, Any]:
            """List all proposals"""
            
            proposal_list = []
            for proposal in self.proposals:
                proposal_list.append({
                    "workflow_id": proposal.workflow_id,
                    "workflow_type": proposal.workflow_type.value,
                    "confidence": proposal.confidence,
                    "status": proposal.approval_status.value,
                    "created_at": proposal.created_at.isoformat()
                })
            
            return {
                "success": True,
                "total_proposals": len(proposal_list),
                "proposals": proposal_list,
            }
        
        tools.append(list_proposals)
        
        return tools
    
    async def process_email(self, email_data: Dict[str, Any]) -> ProposedWorkflow:
        """Process a single email and generate a workflow proposal with tracing"""
        
        logger.info(f"Processing email for proposal: {email_data.get('subject', 'No subject')}")
        
        # Create trace name based on email
        trace_name = f"Proposal_Generation_{email_data.get('subject', 'No_subject')[:30]}"
        
        # Use trace context for monitoring
        with trace(trace_name):
            # Start monitoring this trace
            trace_monitor.start_trace(
                trace_name,
                {
                    "email_from": email_data.get("from", "Unknown"),
                    "email_subject": email_data.get("subject", "No subject"),
                    "orchestrator_version": "v4_proposal",
                    "mode": "proposal_generation"
                }
            )
            
            try:
                # Prepare prompt for agent
                prompt = f"""Process this email and generate a complete workflow proposal:
                
Subject: {email_data.get('subject', 'No subject')}
From: {email_data.get('from', 'unknown@email.com')}
Body: {email_data.get('body', 'No body')}
Attachments: {email_data.get('attachments', [])}

Instructions:
1. Use classify_email_intent to understand the email type
2. Use search_inventory_for_proposal if the email mentions specific products
3. Use analyze_attachments_for_proposal if there are attachments
4. Use get_customer_context to retrieve customer history
5. Use generate_workflow_proposal to create the main proposal
6. Use enrich_proposal_with_context to add business context
7. Return the workflow_id of the generated proposal"""
                
                # Run the agent to generate proposal
                result = await self.runner.run(self.agent, prompt)
                
                # Extract tool calls from result for tracing
                tool_calls = []
                if hasattr(result, 'raw_responses'):
                    for response in result.raw_responses:
                        if hasattr(response, 'model_response'):
                            model_resp = response.model_response
                            if hasattr(model_resp, 'choices'):
                                for choice in model_resp.choices:
                                    if hasattr(choice, 'message') and hasattr(choice.message, 'tool_calls'):
                                        if choice.message.tool_calls:
                                            for tc in choice.message.tool_calls:
                                                tool_call = {
                                                    "tool": tc.function.name if hasattr(tc.function, 'name') else "unknown",
                                                    "args": json.loads(tc.function.arguments) if hasattr(tc.function, 'arguments') else {},
                                                    "result": "See logs"
                                                }
                                                tool_calls.append(tool_call)
                                                # Add to trace monitor
                                                trace_monitor.add_tool_call(
                                                    tool_name=tool_call["tool"],
                                                    args=tool_call["args"],
                                                    result=tool_call["result"]
                                                )
                
                # Log trace information
                logger.info(f"Trace created: {trace_name}")
                logger.info(f"Proposal generation tool calls: {len(tool_calls)}")
                
                # Find the most recent proposal
                proposal = None
                if self.proposals:
                    proposal = self.proposals[-1]
                
                # Add proposal details to trace
                if proposal:
                    trace_monitor.add_decision(
                        decision_type="proposal_generated",
                        details={
                            "workflow_id": proposal.workflow_id,
                            "workflow_type": proposal.workflow_type.value,
                            "confidence": proposal.confidence,
                            "actions_count": len(proposal.proposed_actions),
                        }
                    )
                
                # End trace with summary
                final_output = f"Generated proposal {proposal.workflow_id if proposal else 'None'}"
                trace_monitor.end_trace("completed", final_output)
                
                return proposal
                
            except Exception as e:
                logger.error(f"Error in proposal generation: {e}")
                trace_monitor.end_trace("failed", str(e))
                raise
    
    async def start_monitoring(self, interval_seconds: int = 30):
        """Start monitoring emails and generating proposals with tracing"""
        self.is_monitoring = True
        logger.info(f"Starting email monitoring every {interval_seconds} seconds")
        
        cycle_count = 0
        while self.is_monitoring:
            cycle_count += 1
            trace_name = f"Proposal_Monitoring_Cycle_{cycle_count}"
            
            with trace(trace_name):
                try:
                    # Start monitoring trace
                    trace_monitor.start_trace(
                        trace_name,
                        {
                            "cycle": cycle_count,
                            "orchestrator_version": "v4_proposal",
                            "mode": "monitoring"
                        }
                    )
                    
                    # Check for new emails
                    emails = await self.gmail_agent.poll_emails() if self.gmail_agent else []
                    
                    proposals_generated = []
                    for email in emails:
                        logger.info(f"Processing email: {email.get('subject', 'No subject')}")
                        
                        # Generate proposal for this email
                        proposal = await self.process_email(email)
                        
                        if proposal:
                            proposals_generated.append(proposal.workflow_id)
                            logger.info(f"Generated proposal {proposal.workflow_id} with confidence {proposal.confidence:.2%}")
                    
                    # End monitoring cycle trace
                    summary = f"Cycle {cycle_count}: Processed {len(emails)} emails, generated {len(proposals_generated)} proposals"
                    trace_monitor.end_trace("completed", summary)
                    logger.info(summary)
                    
                    # Wait before next check
                    await asyncio.sleep(interval_seconds)
                    
                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    trace_monitor.end_trace("failed", str(e))
                    await asyncio.sleep(interval_seconds)
    
    def stop_monitoring(self):
        """Stop email monitoring"""
        self.is_monitoring = False
        logger.info("Stopped email monitoring")
    
    def get_all_proposals(self) -> List[ProposedWorkflow]:
        """Get all generated proposals"""
        return self.proposals
    
    def get_proposal_by_id(self, workflow_id: str) -> Optional[ProposedWorkflow]:
        """Get a specific proposal by ID"""
        for proposal in self.proposals:
            if proposal.workflow_id == workflow_id:
                return proposal
        return None
    
    def approve_proposal(self, workflow_id: str, approver: str = "system") -> bool:
        """Mark a proposal as approved (does not execute)"""
        proposal = self.get_proposal_by_id(workflow_id)
        if proposal:
            proposal.approval_status = ApprovalStatus.APPROVED
            proposal.approved_by = approver
            proposal.approved_at = datetime.now()
            logger.info(f"Proposal {workflow_id} approved by {approver}")
            return True
        return False
    
    def reject_proposal(self, workflow_id: str, reason: str = "") -> bool:
        """Mark a proposal as rejected"""
        proposal = self.get_proposal_by_id(workflow_id)
        if proposal:
            proposal.approval_status = ApprovalStatus.REJECTED
            proposal.approval_notes = reason
            logger.info(f"Proposal {workflow_id} rejected: {reason}")
            return True
        return False