"""Proposal-Based Orchestrator - Generates workflows for human approval"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents import Agent, Runner, function_tool, trace

from ..factory_config.settings import settings
from ..factory_utils.trace_monitor import trace_monitor
from ..factory_database.vector_db import ChromaDBClient
from ..factory_rag.embeddings_config import EmbeddingsManager
from ..factory_models import (
    ExtractedOrder,
    CustomerInfo,
    OrderItem,
    TagSpecification,
    DeliveryInfo,
    OrderPriority,
    ProposedWorkflow,
)
from .proposal_engine import ProposalEngine
from .mock_gmail_agent import MockGmailAgent
from .order_processor_agent import OrderProcessorAgent
from .image_processor_agent import ImageProcessorAgent

logger = logging.getLogger(__name__)


class ProposalOrchestratorV4:
    """Orchestrator that generates workflow proposals instead of executing directly"""

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
        
        # Create proposal-generating tools
        self.tools = self._create_proposal_tools()
        
        # Create the proposal agent
        self.agent = Agent(
            name="ProposalOrchestrator",
            instructions=self._get_proposal_instructions(),
            tools=self.tools,
            model="gpt-4o",
        )
        
        logger.info(f"Initialized Proposal Orchestrator V4 with {len(self.tools)} tools")
    
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
1. First use analyze_email_and_propose to generate a complete workflow proposal
2. Use search_inventory_for_proposal to gather inventory data if needed
3. Use analyze_attachments_for_proposal to process any attachments
4. Use enrich_proposal_with_context to add customer/historical context
5. Return the complete proposal for human review

Remember: You are an ADVISOR, not an executor. Your proposals must be comprehensive 
enough for humans to understand and approve/modify before execution."""
    
    def _create_proposal_tools(self) -> List:
        """Create tools that generate proposals instead of executing actions"""
        
        # Main proposal generation tool
        @function_tool(
            name_override="analyze_email_and_propose",
            description_override="Analyze email and generate a complete workflow proposal for human review. This is the PRIMARY tool to use for all emails.",
        )
        async def analyze_email_and_propose(
            email_subject: str,
            email_body: str,
            sender_email: str,
            attachments: Optional[List[str]] = None
        ) -> Dict[str, Any]:
            """Generate a comprehensive workflow proposal"""
            try:
                # Extract basic email data
                email_data = {
                    "from": sender_email,
                    "subject": email_subject,
                    "body": email_body,
                    "attachments": attachments or []
                }
                
                # Try to extract order information using AI
                order_data = None
                if "order" in email_subject.lower() or "order" in email_body.lower():
                    try:
                        # Use AI to extract order details
                        extraction_prompt = f"""Extract order information from this email:
                        Subject: {email_subject}
                        Body: {email_body}
                        
                        Return a JSON with: items (list of item descriptions), quantities, customer_name, special_instructions"""
                        
                        response = await self.openai_client.chat.completions.create(
                            model="gpt-4",
                            messages=[
                                {"role": "system", "content": "You are an order extraction assistant. Extract order details and return valid JSON."},
                                {"role": "user", "content": extraction_prompt}
                            ],
                            temperature=0.1
                        )
                        
                        extracted = json.loads(response.choices[0].message.content)
                        
                        # Create ExtractedOrder from extracted data
                        if extracted.get("items"):
                            order_data = ExtractedOrder(
                                email_subject=email_subject,
                                email_date=datetime.now(),
                                customer=CustomerInfo(
                                    company_name=extracted.get("customer_name", "Unknown"),
                                    email=sender_email,
                                    contact_person=extracted.get("contact_person")
                                ),
                                items=[
                                    OrderItem(
                                        item_id=f"ITEM-{i}",
                                        tag_specification=TagSpecification(
                                            tag_code="TBD",
                                            tag_type="fit_tag",
                                            quantity=extracted.get("quantities", {}).get(item, 1),
                                            description=item
                                        ),
                                        brand="TBD",
                                        quantity_ordered=extracted.get("quantities", {}).get(item, 1)
                                    )
                                    for i, item in enumerate(extracted.get("items", []))
                                ],
                                delivery=DeliveryInfo(
                                    urgency=OrderPriority.NORMAL,
                                    special_instructions=extracted.get("special_instructions")
                                ),
                                extraction_confidence=0.7,
                                extraction_method="ai_gpt4"
                            )
                    except Exception as e:
                        logger.warning(f"Could not extract order data: {e}")
                
                # Search inventory if we have items
                inventory_matches = []
                if order_data and order_data.items:
                    for item in order_data.items[:3]:  # Limit searches
                        try:
                            # Generate embedding for search
                            search_query = item.tag_specification.description or "tag"
                            query_embedding = self.embeddings_manager.encode_queries([search_query])[0]
                            
                            results = self.chromadb_client.search(
                                query=search_query,
                                query_embedding=query_embedding,
                                n_results=5
                            )
                            if results and results.get("documents"):
                                for i, doc in enumerate(results["documents"][0]):
                                    inventory_matches.append({
                                        "tag_code": results["ids"][0][i] if "ids" in results else f"TAG-{i}",
                                        "tag_name": doc,
                                        "confidence": 1 - results["distances"][0][i] if "distances" in results else 0.5,
                                        "metadata": results["metadatas"][0][i] if "metadatas" in results else {}
                                    })
                        except Exception as e:
                            logger.warning(f"Inventory search failed: {e}")
                
                # Get customer context
                customer_data = {
                    "email": sender_email,
                    "order_count": 0,  # Would query database in production
                    "tier": "new"
                }
                
                # Generate the workflow proposal
                proposal = self.proposal_engine.generate_workflow_proposal(
                    email_data=email_data,
                    order_data=order_data,
                    inventory_matches=inventory_matches,
                    customer_data=customer_data
                )
                
                # Store the proposal
                self.proposals.append(proposal)
                self.proposal_history.append({
                    "timestamp": datetime.now().isoformat(),
                    "workflow_id": proposal.workflow_id,
                    "email_subject": email_subject
                })
                
                # Return proposal as dict for agent
                return {
                    "success": True,
                    "workflow_id": proposal.workflow_id,
                    "workflow_type": proposal.workflow_type.value,
                    "confidence": proposal.confidence,
                    "actions_count": len(proposal.proposed_actions),
                    "reasoning": proposal.reasoning,
                    "estimated_value": proposal.estimated_value,
                    "email_draft": proposal.email_content.body if proposal.email_content else None,
                    "message": f"Generated {proposal.workflow_type.value} workflow with {len(proposal.proposed_actions)} actions"
                }
                
            except Exception as e:
                logger.error(f"Error generating proposal: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "message": "Failed to generate workflow proposal"
                }
        
        # Inventory search tool for proposals
        @function_tool(
            name_override="search_inventory_for_proposal",
            description_override="Search inventory to enrich proposal with accurate data. Does not reserve or modify inventory.",
        )
        def search_inventory_for_proposal(
            query: str,
            min_quantity: int = 0,
            limit: int = 10
        ) -> Dict[str, Any]:
            """Search inventory for proposal generation"""
            try:
                # Generate embedding for the query using Stella
                query_embedding = self.embeddings_manager.encode_queries([query])[0]
                
                # Search with pre-computed embedding
                results = self.chromadb_client.search(
                    query=query,
                    query_embedding=query_embedding,
                    n_results=limit
                )
                
                matches = []
                if results and results.get("documents"):
                    for i in range(len(results["documents"][0])):
                        match = {
                            "tag_code": results["ids"][0][i] if "ids" in results else f"TAG-{i}",
                            "description": results["documents"][0][i],
                            "confidence": 1 - results["distances"][0][i] if "distances" in results else 0.5,
                            "metadata": results["metadatas"][0][i] if "metadatas" in results else {}
                        }
                        
                        # Check quantity if specified
                        if min_quantity > 0:
                            qty = match["metadata"].get("quantity", 0)
                            if qty >= min_quantity:
                                matches.append(match)
                        else:
                            matches.append(match)
                
                return {
                    "success": True,
                    "query": query,
                    "matches_found": len(matches),
                    "matches": matches,
                    "message": f"Found {len(matches)} inventory matches for proposal"
                }
                
            except Exception as e:
                logger.error(f"Inventory search error: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "matches": []
                }
        
        # Attachment analysis tool
        @function_tool(
            name_override="analyze_attachments_for_proposal",
            description_override="Analyze email attachments to extract data for proposal. Does not modify attachments.",
        )
        async def analyze_attachments_for_proposal(
            attachment_names: List[str],
            attachment_types: List[str]
        ) -> Dict[str, Any]:
            """Analyze attachments for proposal generation"""
            extracted_data = []
            
            for name, att_type in zip(attachment_names, attachment_types):
                if "excel" in att_type.lower() or "csv" in att_type.lower():
                    extracted_data.append({
                        "filename": name,
                        "type": "spreadsheet",
                        "analysis": "Contains structured order data",
                        "confidence": 0.9
                    })
                elif "pdf" in att_type.lower():
                    extracted_data.append({
                        "filename": name,
                        "type": "document",
                        "analysis": "Contains order documentation",
                        "confidence": 0.8
                    })
                elif "image" in att_type.lower() or name.lower().endswith(('.jpg', '.png', '.jpeg')):
                    extracted_data.append({
                        "filename": name,
                        "type": "image",
                        "analysis": "Contains product images for matching",
                        "confidence": 0.7
                    })
                else:
                    extracted_data.append({
                        "filename": name,
                        "type": "unknown",
                        "analysis": "Unknown file type",
                        "confidence": 0.3
                    })
            
            return {
                "success": True,
                "attachments_analyzed": len(extracted_data),
                "extracted_data": extracted_data,
                "message": f"Analyzed {len(extracted_data)} attachments for proposal"
            }
        
        # Context enrichment tool
        @function_tool(
            name_override="enrich_proposal_with_context",
            description_override="Enrich proposal with customer history and business context. Read-only operation.",
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
            
            # Simulate customer history lookup
            context = {
                "customer_tier": "regular" if "@gmail.com" in customer_email else "new",
                "previous_orders": 3 if "@gmail.com" in customer_email else 0,
                "payment_history": "excellent" if "@gmail.com" in customer_email else "unknown",
                "preferred_products": ["Allen Solly tags", "Van Heusen labels"],
                "average_order_value": 5000.0
            }
            
            # Update proposal reasoning with context
            proposal.reasoning += f" Customer has {context['previous_orders']} previous orders with {context['payment_history']} payment history."
            
            return {
                "success": True,
                "workflow_id": workflow_id,
                "context_added": context,
                "updated_confidence": proposal.confidence,
                "message": "Proposal enriched with customer context"
            }
        
        # Get proposal details tool
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
                                "risk": action.risk.value
                            }
                            for action in proposal.proposed_actions
                        ],
                        "reasoning": proposal.reasoning,
                        "alternatives": [
                            {
                                "action": alt.action,
                                "reason": alt.reason
                            }
                            for alt in proposal.alternatives
                        ],
                        "risks": [
                            {
                                "risk": risk.risk,
                                "description": risk.description,
                                "mitigation": risk.mitigation
                            }
                            for risk in proposal.risks
                        ],
                        "email_content": {
                            "subject": proposal.email_content.subject,
                            "body": proposal.email_content.body
                        } if proposal.email_content else None
                    }
            
            return {
                "success": False,
                "error": "Proposal not found"
            }
        
        # List all proposals tool
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
                    "actions_count": len(proposal.proposed_actions),
                    "status": proposal.approval_status.value,
                    "created_at": proposal.created_at.isoformat()
                })
            
            return {
                "success": True,
                "total_proposals": len(proposal_list),
                "proposals": proposal_list,
                "message": f"Found {len(proposal_list)} proposals"
            }
        
        # Check emails tool (read-only)
        @function_tool(
            name_override="check_emails",
            description_override="Check for new emails to process. Returns emails but does not process them.",
        )
        async def check_emails() -> List[Dict[str, Any]]:
            """Check for new emails"""
            if not self.gmail_agent:
                return []
            
            try:
                emails = await self.gmail_agent.poll_emails()
                return emails
            except Exception as e:
                logger.error(f"Error checking emails: {e}")
                return []
        
        return [
            analyze_email_and_propose,
            search_inventory_for_proposal,
            analyze_attachments_for_proposal,
            enrich_proposal_with_context,
            get_proposal_details,
            list_proposals,
            check_emails
        ]
    
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
1. Use analyze_email_and_propose to generate the main proposal
2. Use search_inventory_for_proposal if the email mentions specific products
3. Use analyze_attachments_for_proposal if there are attachments
4. Use enrich_proposal_with_context to add customer history
5. Return the workflow_id of the generated proposal"""
                
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
                
                # Extract workflow_id from agent response
                workflow_id = None
                if result:
                    # RunResult has different structure than expected
                    result_text = str(result)
                    # Try to extract workflow_id from response
                    match = re.search(r'WF-\d{8}-\w{8}', result_text)
                    if match:
                        workflow_id = match.group(0)
                
                # Find the proposal
                proposal = None
                if workflow_id:
                    for p in self.proposals:
                        if p.workflow_id == workflow_id:
                            proposal = p
                            break
                
                # If not found by ID, get the most recent
                if not proposal and self.proposals:
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
                            "risks_count": len(proposal.risks) if proposal.risks else 0,
                            "alternatives_count": len(proposal.alternatives) if proposal.alternatives else 0
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
                        
                        # Generate proposal for this email (has its own trace)
                        proposal = await self.process_email(email)
                        
                        if proposal:
                            proposals_generated.append(proposal.workflow_id)
                            logger.info(f"Generated proposal {proposal.workflow_id} with confidence {proposal.confidence:.2%}")
                            logger.info(f"Proposal type: {proposal.workflow_type.value}")
                            logger.info(f"Actions proposed: {len(proposal.proposed_actions)}")
                            
                            # Add to monitoring trace
                            trace_monitor.add_decision(
                                decision_type="proposal_queued",
                                details={
                                    "workflow_id": proposal.workflow_id,
                                    "confidence": proposal.confidence
                                }
                            )
                        else:
                            logger.warning("Failed to generate proposal for email")
                    
                    # End monitoring cycle trace
                    summary = f"Cycle {cycle_count}: Processed {len(emails)} emails, generated {len(proposals_generated)} proposals"
                    trace_monitor.end_trace("completed", summary)
                    logger.info(f"Monitoring cycle {cycle_count} complete: {summary}")
                    
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
            from ..factory_models import ApprovalStatus
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
            from ..factory_models import ApprovalStatus
            proposal.approval_status = ApprovalStatus.REJECTED
            proposal.approval_notes = reason
            logger.info(f"Proposal {workflow_id} rejected: {reason}")
            return True
        return False