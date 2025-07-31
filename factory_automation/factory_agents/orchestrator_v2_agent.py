"""AI-powered orchestrator agent using OpenAI function tools pattern."""

import logging
import time
from typing import Any, Dict

from agents import Agent, Runner
from factory_agents.base import BaseAgent
from factory_agents.email_monitor_agent import EmailMonitorAgent
from factory_agents.inventory_matcher_agent import InventoryMatcherAgent
from factory_agents.order_interpreter_agent import OrderInterpreterAgent

# TODO: Implement these agents
# from factory_agents.document_creator import DocumentCreatorAgent
# from factory_agents.payment_tracker import PaymentTrackerAgent
# from factory_agents.approval_manager import ApprovalManagerAgent
from factory_rag.chromadb_client import ChromaDBClient

# TODO: Implement database CRUD operations
# from factory_database.crud import get_customer_history, get_thread_history

logger = logging.getLogger(__name__)

ORCHESTRATOR_INSTRUCTIONS = """
You are the Factory Automation Orchestrator managing a garment price tag 
manufacturing workflow. You analyze incoming emails and coordinate appropriate 
actions based on context and conversation history.

Your capabilities:
- Analyze emails to understand intent (new orders, payments, follow-ups, queries)
- Extract relevant information and route to appropriate tools
- Maintain context across email threads
- Handle complex scenarios like urgent orders, special discounts, or modified requests
- Ensure human approval for critical decisions

Based on email content, follow these workflows:

1. For new orders: 
   - Use email_monitor to analyze the email
   - Use order_interpreter to extract order details from attachments
   - Use inventory_matcher to find similar tags in inventory
   - Use approval_manager to get human approval for matches
   - Use document_creator to generate PI and response

2. For payments: 
   - Use payment_tracker to extract payment info (UTR/cheque)
   - Verify payment against orders
   - Update order status

3. For follow-ups: 
   - Check order/payment status
   - Provide appropriate updates
   - Handle any modifications

4. For modifications:
   - Understand what needs to be changed
   - Update order details
   - Notify relevant parties

Always consider the full context including:
- Email thread history
- Customer's past orders and preferences
- Any special instructions or urgency
- Business rules and constraints

Make intelligent decisions based on the situation. If uncertain, use the 
approval_manager to get human input.
"""


class OrchestratorAgentV2:
    """AI-powered orchestrator using function tools pattern."""

    def __init__(self, chromadb_client: ChromaDBClient):
        """Initialize orchestrator with all sub-agents as tools."""
        self.chromadb_client = chromadb_client
        self.runner = Runner()

        # Initialize sub-agents
        self.email_monitor = EmailMonitorAgent()
        self.order_interpreter = OrderInterpreterAgent()
        self.inventory_matcher = InventoryMatcherAgent(chromadb_client)
        # TODO: Implement these agents
        # self.document_creator = DocumentCreatorAgent()
        # self.payment_tracker = PaymentTrackerAgent()
        # self.approval_manager = ApprovalManagerAgent()

        # Create orchestrator agent with all agents as tools
        self.agent = Agent(
            name="FactoryOrchestrator",
            instructions=ORCHESTRATOR_INSTRUCTIONS,
            tools=[
                self.email_monitor.as_tool(
                    tool_name="email_monitor",
                    tool_description="Analyze emails to determine type and extract key information",
                ),
                self.order_interpreter.as_tool(
                    tool_name="order_interpreter",
                    tool_description="Extract order details from emails and attachments, analyze tag images",
                ),
                self.inventory_matcher.as_tool(
                    tool_name="inventory_matcher",
                    tool_description="Search inventory for matching tags using multimodal RAG (text + image)",
                ),
                # TODO: Add these tools when agents are implemented
                # self.document_creator.as_tool(
                #     tool_name="document_creator",
                #     tool_description="Generate Pro-forma invoices and professional email responses"
                # ),
                # self.payment_tracker.as_tool(
                #     tool_name="payment_tracker",
                #     tool_description="Process payment confirmations, extract UTR/cheque details"
                # ),
                # self.approval_manager.as_tool(
                #     tool_name="approval_manager",
                #     tool_description="Get human approval for order matches and critical decisions"
                # ),
            ],
            model="gpt-4o",
        )

        logger.info("Initialized AI-powered orchestrator with function tools")

    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an email with full context awareness.

        Args:
            email_data: Email data dictionary containing:
                - subject: Email subject
                - body: Email body
                - sender: Sender email
                - attachments: List of attachments
                - thread_id: Gmail thread ID
                - message_id: Gmail message ID

        Returns:
            Processing result with actions taken
        """
        logger.info(f"Processing email: {email_data.get('subject', 'No subject')}")

        # Track processing time and costs
        start_time = time.time()

        try:
            # Get conversation history
            # TODO: Implement get_thread_history and get_customer_history
            thread_history = []  # await get_thread_history(email_data.get("thread_id"))
            customer_history = (
                []
            )  # await get_customer_history(email_data.get("sender"))

            # Prepare comprehensive context
            context = {
                "current_email": email_data,
                "thread_history": thread_history,
                "customer_history": customer_history,
                "timestamp": email_data.get("timestamp"),
            }

            # Construct prompt for the orchestrator
            prompt = f"""
            Process this email and take appropriate actions:
            
            Email Details:
            - From: {email_data.get('sender')}
            - Subject: {email_data.get('subject')}
            - Body: {email_data.get('body')}
            - Attachments: {len(email_data.get('attachments', []))} files
            
            Thread Context:
            - Previous messages in thread: {len(thread_history)}
            - Customer order history: {len(customer_history)} previous orders
            
            Analyze the email intent and execute the appropriate workflow.
            Provide a summary of actions taken and results.
            """

            # Let the AI orchestrator handle the email
            result = await self.runner.run(self.agent, prompt, context=context)

            # Extract and return results
            processing_result = {
                "success": True,
                "email_id": email_data.get("message_id"),
                "actions_taken": result.final_output,
                "context_used": {
                    "thread_messages": len(thread_history),
                    "customer_orders": len(customer_history),
                },
            }

        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            processing_result = {
                "success": False,
                "email_id": email_data.get("message_id"),
                "error": str(e),
            }

        # Calculate processing time and estimated cost
        processing_time = time.time() - start_time

        # Estimate API cost (rough calculation)
        # GPT-4 costs approximately $0.03 per 1K tokens
        estimated_tokens = len(str(prompt)) / 4  # Rough token estimate
        estimated_cost = (estimated_tokens / 1000) * 0.03

        # Log for comparison if enabled
        from factory_config.settings import settings

        if settings.enable_comparison_logging:
            from factory_utils.comparison_logger import comparison_logger

            comparison_logger.log_processing(
                email_id=email_data.get("message_id", "unknown"),
                orchestrator_version="v2",
                processing_time=processing_time,
                result=processing_result,
                api_cost=estimated_cost,
            )

        return processing_result

    async def handle_complex_request(
        self, request: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle complex requests that don't come from email.

        Args:
            request: Natural language request
            context: Additional context

        Returns:
            Processing result
        """
        try:
            result = await self.runner.run(self.agent, request, context=context)

            return {"success": True, "result": result.final_output}

        except Exception as e:
            logger.error(f"Error handling request: {str(e)}")
            return {"success": False, "error": str(e)}


# Placeholder classes for agents that don't exist yet
class DocumentCreatorAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Document Creator",
            instructions="Generate Pro-forma invoices and professional email responses.",
        )


class PaymentTrackerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Payment Tracker",
            instructions="Process payment confirmations and extract UTR/cheque details.",
        )


class ApprovalManagerAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="Approval Manager",
            instructions="Coordinate human approval for critical decisions.",
        )
