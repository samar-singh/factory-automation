"""Enhanced Orchestrator with Human Interaction Integration"""

import asyncio
import logging
from typing import Any, Dict, Optional

from agents import Agent, function_tool

from ..factory_database.vector_db import ChromaDBClient
from .human_interaction_manager import HumanInteractionManager, Priority
from .orchestrator_v3_agentic import AgenticOrchestratorV3

logger = logging.getLogger(__name__)


class OrchestratorWithHuman(AgenticOrchestratorV3):
    """Orchestrator enhanced with human-in-the-loop capabilities"""

    def __init__(self, chromadb_client: ChromaDBClient, use_mock_gmail: bool = True):
        """Initialize with human interaction support"""
        super().__init__(chromadb_client, use_mock_gmail)

        # Initialize human interaction manager
        self.human_manager = HumanInteractionManager()

        # Register notification handler
        self.human_manager.register_notification_handler(
            self._handle_review_notification
        )

        # Update the order processor with human manager
        self.order_processor.human_manager = self.human_manager

        # Add human interaction tools to the agent
        self._add_human_tools()

        logger.info("Initialized Orchestrator with Human Interaction support")

    def _add_human_tools(self):
        """Add human interaction tools to the agent"""

        # Create review request tool
        @function_tool(
            name_override="create_human_review",
            description_override="Create a review request for manual approval when confidence is 60-80%",
        )
        async def create_human_review(
            email_data: str,
            search_results: str,
            confidence_score: float,
            extracted_items: str,
        ) -> str:
            """Create human review request"""

            import json

            # Parse inputs - handle both string and dict/list inputs
            try:
                # Handle email_data
                if isinstance(email_data, dict):
                    email_dict = email_data
                elif isinstance(email_data, str) and email_data.strip():
                    email_dict = json.loads(email_data)
                else:
                    email_dict = {}

                # Handle search_results
                if isinstance(search_results, list):
                    results_list = search_results
                elif isinstance(search_results, str) and search_results.strip():
                    results_list = json.loads(search_results)
                else:
                    results_list = []

                # Handle extracted_items
                if isinstance(extracted_items, list):
                    items_list = extracted_items
                elif isinstance(extracted_items, str) and extracted_items.strip():
                    items_list = json.loads(extracted_items)
                else:
                    items_list = []

            except json.JSONDecodeError as e:
                logger.error(f"Error parsing review inputs - JSON decode error: {e}")
                logger.debug(
                    f"email_data type: {type(email_data)}, value: {email_data}"
                )
                logger.debug(
                    f"search_results type: {type(search_results)}, value: {search_results}"
                )
                logger.debug(
                    f"extracted_items type: {type(extracted_items)}, value: {extracted_items}"
                )
                return f"Error: Failed to parse inputs - {str(e)}"
            except Exception as e:
                logger.error(f"Error parsing review inputs - unexpected error: {e}")
                return f"Error: Failed to parse inputs - {str(e)}"

            # Create review request
            review = await self.human_manager.create_review_request(
                email_data=email_dict,
                search_results=(
                    results_list if isinstance(results_list, list) else [results_list]
                ),
                confidence_score=confidence_score,
                extracted_items=(
                    items_list if isinstance(items_list, list) else [items_list]
                ),
            )

            return f"Created review request {review.request_id} with {review.priority.value} priority. Status: {review.status.value}"

        # Check review status tool
        @function_tool(
            name_override="check_review_status",
            description_override="Check the status of a human review request",
        )
        async def check_review_status(request_id: str) -> str:
            """Check review status"""

            review = await self.human_manager.get_review_details(request_id)

            if not review:
                return f"Review {request_id} not found"

            status_info = {
                "request_id": review.request_id,
                "status": review.status.value,
                "priority": review.priority.value,
                "confidence_score": review.confidence_score,
                "assigned_to": review.assigned_to,
                "decision": review.decision,
                "notes": review.review_notes,
            }

            if review.reviewed_at:
                review_time = (review.reviewed_at - review.created_at).total_seconds()
                status_info["review_time_seconds"] = review_time

            import json

            return json.dumps(status_info)

        # Get pending reviews tool
        @function_tool(
            name_override="get_pending_reviews",
            description_override="Get list of pending human reviews",
        )
        async def get_pending_reviews(priority: Optional[str] = None) -> str:
            """Get pending reviews"""

            priority_enum = None
            if priority:
                try:
                    priority_enum = Priority[priority.upper()]
                except KeyError:
                    return f"Invalid priority: {priority}"

            reviews = await self.human_manager.get_pending_reviews(
                priority_filter=priority_enum
            )

            review_list = []
            for review in reviews[:10]:  # Limit to 10 for response size
                review_list.append(
                    {
                        "request_id": review.request_id,
                        "customer": review.customer_email,
                        "subject": review.subject[:50],
                        "confidence": review.confidence_score,
                        "priority": review.priority.value,
                        "status": review.status.value,
                        "created_at": review.created_at.isoformat(),
                    }
                )

            import json

            return json.dumps({"total_pending": len(reviews), "reviews": review_list})

        # Process review decision tool
        @function_tool(
            name_override="process_review_decision",
            description_override="Process the decision from a human review",
        )
        async def process_review_decision(request_id: str) -> str:
            """Process review decision"""

            review = await self.human_manager.get_review_details(request_id)

            if not review:
                return f"Review {request_id} not found"

            if review.status.value not in [
                "approved",
                "rejected",
                "alternative_suggested",
            ]:
                return f"Review {request_id} is still {review.status.value}"

            # Based on decision, take action
            action_taken = "No action needed"

            if review.status.value == "approved":
                action_taken = "Proceed with order processing and quotation generation"
            elif review.status.value == "rejected":
                action_taken = "Send rejection email to customer with reason"
            elif review.status.value == "alternative_suggested":
                action_taken = f"Send alternative suggestions to customer: {len(review.alternative_items)} items"

            return f"Review {request_id} decision: {review.decision}. Action: {action_taken}"

        # Add tools to agent
        self.tools.extend(
            [
                create_human_review,
                check_review_status,
                get_pending_reviews,
                process_review_decision,
            ]
        )

        # Update agent with new tools
        self.agent = Agent(
            name="FactoryAutomationOrchestratorWithHuman",
            instructions=self._get_enhanced_instructions(),
            tools=self.tools,
            model="gpt-4o",
        )

    def _get_enhanced_instructions(self) -> str:
        """Get enhanced instructions including human interaction"""

        return """You are an autonomous factory automation orchestrator for a garment price tag manufacturing facility with human-in-the-loop support.

Your responsibilities:
1. Monitor and process incoming order emails
2. Extract order details from emails and attachments
3. Search inventory for matching products
4. Make approval decisions based on match quality
5. Create human review requests when confidence is medium
6. Generate quotations and confirmations
7. Track payments and update order status

Available tools:
- process_complete_order: Process complete order with extraction, search, and routing
- process_tag_image: Analyze tag images with Qwen2.5VL
- search_inventory: Semantic search in ChromaDB
- search_visual: Visual similarity search
- get_customer_context: Retrieve historical data
- generate_document: Create quotations/confirmations
- update_order_status: Update order in database
- create_human_review: Create manual review request (USE THIS when confidence 60-80%)
- check_review_status: Check status of specific review
- get_pending_reviews: List all pending reviews
- process_review_decision: Handle completed review decision

CRITICAL Decision Rules:
1. When ANY item has similarity score below 90%:
   - MUST use create_human_review tool
   - Include all search results for human review
   - Human will decide to: Approve, Reject, Request Clarification, Suggest Alternatives, or Defer
   
2. Only when ALL items have ≥90% similarity:
   - Auto-approve and generate quotation
   
3. Priority setting for human review:
   - <60% match: HIGH priority (likely needs clarification)
   - 60-80% match: MEDIUM priority
   - 80-90% match: LOW priority
   - Keywords "urgent", "rush", "asap": Always HIGH priority
   
4. For the create_human_review tool:
   - email_data: Pass the original email information as JSON string
   - search_results: Pass the inventory search results as JSON string
   - confidence_score: Pass the average confidence score
   - extracted_items: Pass the extracted order items as JSON string

Workflow:
1. Process order email → Extract items → Search inventory
2. Calculate confidence scores from search results
3. IF any score <80%: IMMEDIATELY use create_human_review
4. Monitor pending reviews and process decisions
5. Generate appropriate documents based on decisions

Remember: ALWAYS create human review when confidence is not high (>80% for ALL items)."""

    async def _handle_review_notification(self, review_request):
        """Handle notifications for new review requests"""

        logger.info(f"New review request: {review_request.request_id}")

        # In production, this could:
        # - Send email notifications
        # - Post to Slack/Teams
        # - Update dashboard
        # - Trigger webhooks

        if review_request.priority == Priority.URGENT:
            logger.warning(f"URGENT review required: {review_request.request_id}")

    async def monitor_reviews(self):
        """Monitor and process completed reviews"""

        logger.info("Starting review monitoring...")

        while self.is_monitoring:
            try:
                # Get pending reviews
                reviews = await self.human_manager.get_pending_reviews()

                for review in reviews:
                    # Check if review has been completed
                    if review.status.value in [
                        "approved",
                        "rejected",
                        "alternative_suggested",
                    ]:
                        # Process the decision
                        logger.info(f"Processing completed review: {review.request_id}")

                        # Let the agent handle the completed review
                        prompt = f"""
A human review has been completed:
Review ID: {review.request_id}
Decision: {review.decision}
Status: {review.status.value}
Notes: {review.review_notes}

Process this decision using the process_review_decision tool and take appropriate action.
"""

                        await self.runner.run(self.agent, prompt)

                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                logger.error(f"Error monitoring reviews: {e}")
                await asyncio.sleep(60)

    def get_review_statistics(self) -> Dict[str, Any]:
        """Get human review statistics"""
        return self.human_manager.get_review_statistics()

    async def start_with_review_monitoring(self):
        """Start orchestrator with review monitoring"""

        # Start email monitoring
        email_task = asyncio.create_task(self.start_email_monitoring())

        # Start review monitoring
        review_task = asyncio.create_task(self.monitor_reviews())

        # Wait for both
        await asyncio.gather(email_task, review_task)


def create_orchestrator_with_human() -> OrchestratorWithHuman:
    """Factory function to create orchestrator with human interaction"""

    chromadb_client = ChromaDBClient()
    return OrchestratorWithHuman(chromadb_client)
