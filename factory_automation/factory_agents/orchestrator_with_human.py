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
            description_override="Create a review request for manual approval based on order processing results",
        )
        async def create_human_review(
            order_id: str,
            review_reason: str,
        ) -> str:
            """Create human review request using data from last processed order"""


            # Get the last order result from the orchestrator
            if not hasattr(self, '_last_order_result') or self._last_order_result is None:
                return "Error: No order has been processed yet. Call process_complete_order first."
            
            result = self._last_order_result
            
            # Verify this is the correct order
            if result.get('order_id') != order_id:
                return f"Error: Order ID mismatch. Expected {result.get('order_id')}, got {order_id}"
            
            # Check if review is needed
            if not result.get('needs_review'):
                return f"Order {order_id} does not need review according to process_complete_order"
            
            # Extract data from the order result
            try:
                # Debug logging
                logger.info(f"Order result keys: {list(result.keys())}")
                logger.info(f"confidence_scores type: {type(result.get('confidence_scores'))}, value: {result.get('confidence_scores')}")
                
                # Prepare email data
                email_dict = {
                    "subject": getattr(self, '_current_email_subject', 'Order Request'),
                    "from": result.get('customer', 'unknown@example.com'),
                    "body": getattr(self, '_current_email_body', '')[:500],
                    "order_id": order_id,
                }
                
                # Get search results (inventory matches)
                inventory_matches = result.get('inventory_matches')
                if inventory_matches is None:
                    results_list = []
                elif isinstance(inventory_matches, list):
                    results_list = inventory_matches[:10]
                elif isinstance(inventory_matches, int):
                    # Sometimes it's just a count
                    results_list = []
                    logger.info(f"inventory_matches is a count: {inventory_matches}")
                else:
                    results_list = []
                    logger.warning(f"inventory_matches unexpected type: {type(inventory_matches)}")
                
                # Get extracted items  
                extracted_items = result.get('extracted_items_for_review')
                if extracted_items is None:
                    items_list = []
                elif isinstance(extracted_items, list):
                    items_list = extracted_items
                else:
                    items_list = []
                    logger.warning(f"extracted_items_for_review is not a list: {type(extracted_items)}")
                logger.info(f"items_list type: {type(items_list)}, length: {len(items_list) if isinstance(items_list, list) else 'N/A'}")
                
                # Get confidence score
                confidence_score = 0.0
                if result.get('confidence_scores'):
                    scores = result['confidence_scores']
                    if isinstance(scores, dict):
                        # Dict with item_id as keys and confidence as values
                        if 'average' in scores:
                            avg_score = scores['average']
                        elif scores:
                            # Calculate average from dict values
                            score_values = [v for v in scores.values() if isinstance(v, (int, float))]
                            avg_score = sum(score_values) / len(score_values) if score_values else 0
                        else:
                            avg_score = 0
                    elif isinstance(scores, list):
                        avg_score = sum(scores) / len(scores) if scores else 0
                    elif isinstance(scores, (int, float)):
                        avg_score = float(scores)
                    else:
                        # Try to get extraction_confidence as fallback
                        avg_score = result.get('extraction_confidence', 0)
                    confidence_score = avg_score
                elif result.get('extraction_confidence'):
                    confidence_score = result['extraction_confidence']
                
                logger.info(f"Creating review for order {order_id} with confidence {confidence_score:.2%}")
                
            except Exception as e:
                logger.error(f"Error extracting data from order result: {e}")
                return f"Error: Failed to extract order data - {str(e)}"

            # Create review request
            # Ensure lists are actually lists
            if not isinstance(results_list, list):
                logger.warning(f"results_list is not a list: {type(results_list)}, value: {results_list}")
                results_list = []
            
            if not isinstance(items_list, list):
                logger.warning(f"items_list is not a list: {type(items_list)}, value: {items_list}")
                items_list = []
            
            review = await self.human_manager.create_review_request(
                email_data=email_dict,
                search_results=results_list,
                confidence_score=confidence_score,
                extracted_items=items_list,
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
                # Learn from the approval - the AI's classification was correct
                if hasattr(review, 'classification') and review.classification:
                    await self.learn_from_feedback(
                        email_id=request_id,
                        actual_intent=review.classification,
                        was_correct=True
                    )
            elif review.status.value == "rejected":
                action_taken = "Send rejection email to customer with reason"
                # Learn from rejection - the AI may have been wrong
                if hasattr(review, 'classification') and review.classification:
                    await self.learn_from_feedback(
                        email_id=request_id,
                        actual_intent=review.classification,
                        was_correct=False
                    )
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
4. DECIDE on approval actions based on confidence and context
5. CREATE human review requests when YOU determine they're needed
6. Generate quotations and confirmations
7. Track payments and update order status

Available tools:
- process_complete_order: Analyzes orders and returns confidence scores (does NOT create reviews)
- create_human_review: Create review request when YOU decide it's needed
- process_tag_image: Analyze tag images with Qwen2.5VL
- search_inventory: Semantic search in ChromaDB
- search_visual: Visual similarity search
- get_customer_context: Retrieve historical data
- generate_document: Create quotations/confirmations
- update_order_status: Update order in database
- check_review_status: Check status of specific review
- get_pending_reviews: List all pending reviews
- process_review_decision: Handle completed review decision

Decision Framework:
1. First, classify the email intent using context-aware classification
2. For NEW_ORDER intents:
   a. Call process_complete_order to analyze the order
   b. Check the response for 'needs_review', 'confidence_scores', and 'recommended_action'
   c. YOU decide whether to:
      - Auto-approve (if confidence > 90% for all items)
      - Create human review (if confidence 60-90% OR special circumstances)
      - Request clarification (if confidence < 60%)
   d. If creating review, use the data from process_complete_order response
3. For other intents, use appropriate tools

Creating Human Reviews:
When process_complete_order returns 'needs_review': true, YOU must:
1. Evaluate the confidence scores and business context
2. Consider factors like:
   - Customer history
   - Order urgency
   - Total order value
   - Special requirements
3. If review is warranted, call create_human_review with ONLY:
   - order_id: The order ID from process_complete_order response
   - review_reason: A brief explanation of why review is needed

IMPORTANT: The create_human_review tool automatically uses data from the last processed order.
Just pass the order_id and reason - DO NOT try to pass JSON data!

Key Points:
- YOU are the decision maker - process_complete_order only provides data
- Create reviews based on YOUR judgment, not automatically
- Consider context beyond just confidence scores
- One order = one review maximum (check if review already exists)"""

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
