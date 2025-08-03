"""Main orchestrator agent that coordinates all other agents."""

import asyncio
import logging
import time
from typing import Any, Dict

from .base import BaseAgent
from .email_monitor_agent import EmailMonitorAgent
from .inventory_matcher_agent import InventoryMatcherAgent
from .order_interpreter_agent import OrderInterpreterAgent
from ..factory_database.vector_db import ChromaDBClient

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    """Main orchestrator that routes requests to specialized agents."""

    def __init__(self, chromadb_client: ChromaDBClient):
        """Initialize orchestrator with all sub-agents."""
        self.chromadb_client = chromadb_client
        self.is_monitoring = False

        # Initialize sub-agents
        self.email_monitor = EmailMonitorAgent()
        self.order_interpreter = OrderInterpreterAgent()
        self.inventory_matcher = InventoryMatcherAgent(chromadb_client)

        # Initialize base agent with handoffs
        super().__init__(
            name="Factory Orchestrator",
            instructions="""You are the main coordinator for the factory automation system.
            Route incoming requests to the appropriate specialized agents:
            - Email processing → Email Monitor Agent
            - Order interpretation → Order Interpreter Agent
            - Inventory matching → Inventory Matcher Agent

            Maintain context across the workflow and ensure smooth handoffs.""",
            handoffs=[
                self.email_monitor.agent,
                self.order_interpreter.agent,
                self.inventory_matcher.agent,
            ],
        )

    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an email through the full workflow.

        Args:
            email_data: Email data dictionary

        Returns:
            Processing result
        """
        logger.info(f"Processing email: {email_data.get('subject', 'No subject')}")

        # Track processing time for comparison
        start_time = time.time()

        try:
            # Step 1: Analyze email
            email_analysis = await self.email_monitor.run(
                f"Analyze this email: {email_data}", context={"email_data": email_data}
            )

            if not email_analysis["success"]:
                return email_analysis

            # Step 2: Based on email type, route appropriately
            email_type = email_analysis.get("context", {}).get("email_type", "unknown")

            if email_type == "new_order":
                # Extract order details
                order_details = await self.order_interpreter.run(
                    f"Extract order details from: {email_data}",
                    context=email_analysis["context"],
                )

                if order_details["success"]:
                    # Find matching inventory
                    matches = await self.inventory_matcher.run(
                        f"Find matches for: {order_details['context']}",
                        context=order_details["context"],
                    )

                    result = {
                        "success": True,
                        "email_type": email_type,
                        "order_details": order_details["context"],
                        "matches": matches["context"].get("matches", []),
                    }

            elif email_type == "payment":
                # Handle payment processing
                result = {
                    "success": True,
                    "email_type": email_type,
                    "message": "Payment email detected - processing not yet implemented",
                }

            else:
                result = {
                    "success": True,
                    "email_type": email_type,
                    "message": "Email type not requiring action",
                }

        except Exception as e:
            logger.error(f"Error processing email: {str(e)}")
            result = {"success": False, "error": str(e)}

        # Log for comparison if enabled
        processing_time = time.time() - start_time
        from ..factory_config.settings import settings

        if settings.enable_comparison_logging:
            from ..factory_utils.comparison_logger import comparison_logger

            comparison_logger.log_processing(
                email_id=email_data.get("message_id", "unknown"),
                orchestrator_version="v1",
                processing_time=processing_time,
                result=result,
            )

        return result

    async def start_email_monitoring(self):
        """Start continuous email monitoring."""
        self.is_monitoring = True
        logger.info("Starting email monitoring...")

        while self.is_monitoring:
            try:
                # Check for new emails
                new_emails = await self.email_monitor.check_new_emails()

                for email in new_emails:
                    await self.process_email(email)

                # Wait for next poll interval
                await asyncio.sleep(300)  # 5 minutes

            except Exception as e:
                logger.error(f"Error in email monitoring: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def stop(self):
        """Stop the orchestrator."""
        self.is_monitoring = False
        logger.info("Orchestrator stopped")

    def is_running(self) -> bool:
        """Check if orchestrator is running."""
        return self.is_monitoring
