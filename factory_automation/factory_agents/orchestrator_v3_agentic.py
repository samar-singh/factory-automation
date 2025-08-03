"""True Agentic Orchestrator - Autonomous AI with tool usage"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents import Agent, Runner, trace, function_tool

from ..factory_config.settings import settings
from ..factory_database.vector_db import ChromaDBClient
from ..factory_utils.trace_monitor import trace_monitor
from .mock_gmail_agent import MockGmailAgent

logger = logging.getLogger(__name__)


class AgenticOrchestratorV3:
    """Fully autonomous orchestrator using OpenAI Agents SDK with callable tools"""

    def __init__(self, chromadb_client: ChromaDBClient):
        """Initialize with ChromaDB and create autonomous agent"""
        self.chromadb_client = chromadb_client
        self.runner = Runner()
        self.is_monitoring = False

        # Initialize mock Gmail for testing
        self.gmail_agent = MockGmailAgent()

        # Tool call tracking
        self.tool_call_history = []

        # Create all tools that the agent can autonomously use
        self.tools = self._create_tools()

        # Create the autonomous agent
        self.agent = Agent(
            name="FactoryAutomationOrchestrator",
            instructions=self._get_agent_instructions(),
            tools=self.tools,
            model="gpt-4o",  # Default model
        )

        logger.info(f"Initialized Agentic Orchestrator V3 with {len(self.tools)} tools")

    def _get_agent_instructions(self) -> str:
        """Get comprehensive instructions for the autonomous agent"""
        return """You are an autonomous factory automation orchestrator for a garment price tag manufacturing facility.

Your responsibilities:
1. Monitor and process incoming order emails
2. Extract order details from emails and attachments
3. Search inventory for matching products using semantic and visual search
4. Make approval decisions based on match quality
5. Generate quotations and confirmations
6. Track payments and update order status

Available tools:
- check_emails: Poll for new emails
- analyze_email: Determine email type and intent
- extract_order_items: Extract structured order details
- search_inventory: Semantic search in ChromaDB
- search_visual: Visual similarity search using CLIP
- get_customer_context: Retrieve historical data
- make_decision: Decide on approval/review
- generate_document: Create quotations/confirmations
- update_order_status: Update order in database

Workflow guidelines:
1. For new orders: analyze → extract → search → decide → generate quote
2. For payments: analyze → extract payment info → update status
3. For queries: analyze → search context → generate response
4. Always consider customer history for better service

Decision thresholds:
- Auto-approve: >80% similarity score
- Manual review: 60-80% similarity
- Find alternatives: <60% similarity

Think step by step and use tools appropriately to handle each email completely."""

    def _create_tools(self) -> List:
        """Create all callable tools for the agent"""
        tools = []

        # Email monitoring tool
        @function_tool(
            name_override="check_emails",
            description_override="Check for new emails in the inbox",
        )
        async def check_emails() -> List[Dict[str, Any]]:
            """Poll for new emails"""
            try:
                messages = (
                    self.gmail_agent.users()
                    .messages()
                    .list(userId="me", q="is:unread", maxResults=5)
                    .execute()
                )

                emails = []
                for msg in messages.get("messages", []):
                    email_data = self.gmail_agent.process_order_email(msg["id"])
                    if email_data:
                        emails.append(email_data)

                return emails
            except Exception as e:
                logger.error(f"Error checking emails: {e}")
                return []

        tools.append(check_emails)

        # Email analysis tool
        @function_tool(
            name_override="analyze_email",
            description_override="Analyze email to determine type, intent, and urgency",
        )
        async def analyze_email(
            subject: str, body: str, from_email: str, attachments: List[str] = None
        ) -> str:
            """Analyze email content"""
            body_lower = body.lower()
            # subject_lower = subject.lower()  # Not used currently

            # Determine email type
            email_type = "query"
            if any(
                word in body_lower for word in ["order", "purchase", "need", "require"]
            ):
                email_type = "order"
            elif any(
                word in body_lower for word in ["payment", "paid", "utr", "transfer"]
            ):
                email_type = "payment"
            elif any(
                word in body_lower for word in ["status", "update", "where", "when"]
            ):
                email_type = "follow_up"

            # Check urgency
            is_urgent = any(
                word in body_lower for word in ["urgent", "asap", "immediately", "rush"]
            )

            # Check key entities
            has_quantity = "Yes" if any(char.isdigit() for char in body) else "No"
            has_attachments = "Yes" if attachments and len(attachments) > 0 else "No"
            mentions_brand = (
                "Yes"
                if any(
                    brand in body.upper()
                    for brand in ["ALLEN", "MYNTRA", "H&M", "ZARA"]
                )
                else "No"
            )

            return f"Type: {email_type}, Urgent: {is_urgent}, Has quantities: {has_quantity}, Has attachments: {has_attachments}, Mentions brand: {mentions_brand}"

        tools.append(analyze_email)

        # Order extraction tool
        @function_tool(
            name_override="extract_order_items",
            description_override="Extract structured order details from email text",
        )
        async def extract_order_items(
            email_body: str, has_attachments: bool = False
        ) -> str:
            """Extract order items and quantities"""
            import re

            items = []

            # Pattern matching for quantities and items
            quantity_patterns = [
                r"(\d+)\s*(pcs|pieces|units|nos|tags)",
                r"quantity[:\s]+(\d+)",
                r"(\d+)\s+(?:black|blue|green|red|white)\s+tags",
            ]

            for pattern in quantity_patterns:
                matches = re.findall(pattern, email_body.lower())
                for match in matches:
                    if isinstance(match, tuple):
                        qty = match[0]
                    else:
                        qty = match

                    # Extract item description around quantity
                    items.append(
                        {
                            "quantity": int(qty),
                            "description": self._extract_item_description(
                                email_body, qty
                            ),
                            "specifications": self._extract_specifications(email_body),
                        }
                    )

            # Process attachments if any
            attachment_items = []
            # if attachments:  # attachments parameter not available here
            #     for att in attachments:
            #         if att.get('mimeType', '').startswith('application/vnd'):
            #             # Excel file - would process in real implementation
            #             attachment_items.append({
            #                 "source": att['filename'],
            #                 "type": "excel",
            #                 "items_count": "unknown"
            #             })

            return json.dumps(
                {
                    "items": items,
                    "attachment_items": attachment_items,
                    "total_items": len(items),
                    "requires_clarification": len(items) == 0,
                }
            )

        tools.append(extract_order_items)

        # Inventory search tool
        @function_tool(
            name_override="search_inventory",
            description_override="Search inventory using semantic similarity in ChromaDB",
        )
        def search_inventory(
            query: str,
            min_quantity: int = 0,
            brand_filter: Optional[str] = None,
            limit: int = 5,
        ) -> List[Dict[str, Any]]:
            """Search ChromaDB for matching inventory"""
            try:
                # Build metadata filter
                where = {}
                if brand_filter:
                    where["brand"] = brand_filter
                if min_quantity > 0:
                    where["stock"] = {"$gte": min_quantity}

                # Query ChromaDB
                results = self.chromadb_client.collection.query(
                    query_texts=[query],
                    n_results=limit,
                    where=where if where else None,
                    include=["metadatas", "distances", "documents"],
                )

                # Format results
                matches = []
                if results and results.get("ids") and len(results["ids"]) > 0:
                    for i in range(len(results["ids"][0])):
                        metadata = results["metadatas"][0][i]
                        similarity = 1 - results["distances"][0][i]

                        matches.append(
                            {
                                "item_id": results["ids"][0][i],
                                "name": metadata.get("trim_name", "Unknown"),
                                "code": metadata.get("trim_code", "N/A"),
                                "brand": metadata.get("brand", "Unknown"),
                                "stock": metadata.get("stock", 0),
                                "price": metadata.get("price", 0),
                                "similarity_score": similarity,
                                "description": (
                                    results["documents"][0][i][:200]
                                    if results["documents"][0][i]
                                    else ""
                                ),
                            }
                        )

                return matches
            except Exception as e:
                logger.error(f"Error searching inventory: {e}")
                return []

        tools.append(search_inventory)

        # Visual search tool
        @function_tool(
            name_override="search_visual",
            description_override="Search inventory by visual features or image description",
        )
        def search_visual(description: str, limit: int = 5) -> List[Dict[str, Any]]:
            """Visual similarity search"""
            try:
                # For now, use text-based search with visual keywords
                visual_query = f"visual appearance {description}"

                results = self.chromadb_client.collection.query(
                    query_texts=[visual_query],
                    n_results=limit,
                    where=(
                        {"has_image": True}
                        if hasattr(self.chromadb_client, "has_image_field")
                        else None
                    ),
                    include=["metadatas", "distances"],
                )

                matches = []
                if results and results.get("ids"):
                    for i in range(len(results["ids"][0])):
                        metadata = results["metadatas"][0][i]
                        similarity = 1 - results["distances"][0][i]

                        matches.append(
                            {
                                "item_id": results["ids"][0][i],
                                "name": metadata.get("trim_name", "Unknown"),
                                "visual_match_score": similarity,
                                "image_available": metadata.get("has_image", False),
                                "visual_features": metadata.get("visual_features", []),
                            }
                        )

                return matches
            except Exception as e:
                logger.error(f"Error in visual search: {e}")
                return []

        tools.append(search_visual)

        # Customer context tool
        @function_tool(
            name_override="get_customer_context",
            description_override="Retrieve customer history and preferences",
        )
        def get_customer_context(customer_email: str) -> str:
            """Get historical context for customer"""
            try:
                # Mock known customers for demo
                known_customers = {
                    "allen.solly@example.com": "Regular customer: 15 orders, prefers black woven tags",
                    "myntra@example.com": "Premium customer: 25 orders, eco-friendly preference",
                    "ops@zara.com": "New customer: 2 orders, leather tags preference",
                }

                if customer_email in known_customers:
                    return known_customers[customer_email]

                # Search for previous orders
                results = self.chromadb_client.collection.query(
                    query_texts=[f"orders from {customer_email}"],
                    n_results=10,
                    where=(
                        {"customer_email": customer_email}
                        if hasattr(self.chromadb_client, "customer_field")
                        else None
                    ),
                    include=["metadatas"],
                )

                order_count = 0
                if results and results.get("metadatas") and results["metadatas"][0]:
                    order_count = len(results["metadatas"][0])

                if order_count > 5:
                    return f"Regular customer: {order_count} previous orders"
                elif order_count > 0:
                    return f"Returning customer: {order_count} previous orders"
                else:
                    return "New customer: No order history"

            except Exception as e:
                logger.error(f"Error getting customer context: {e}")
                return "Customer history unavailable"

        tools.append(get_customer_context)

        # Decision making tool
        @function_tool(
            name_override="make_decision",
            description_override="Make approval decision based on search results",
        )
        def make_decision(
            search_results: str, customer_history: str = "", urgency: bool = False
        ) -> str:
            """Make approval decision"""
            if "No matches found" in search_results:
                return "Decision: No matches - request clarification from customer"

            # Extract confidence scores from search results string
            import re

            scores = re.findall(r"(\d+)% match", search_results)

            if not scores:
                return "Decision: Unable to determine confidence - needs manual review"

            # Get best score
            best_score = max(int(s) for s in scores)

            # Adjust threshold for regular customers
            threshold_adjustment = 0
            if (
                "Regular customer" in customer_history
                or "Premium customer" in customer_history
            ):
                threshold_adjustment = 5  # Lower threshold by 5%

            # Make decision
            if best_score > (80 - threshold_adjustment):
                return f"Decision: Auto-approved ({best_score}% confidence). Action: Generate quotation"
            elif best_score > (60 - threshold_adjustment):
                return f"Decision: Manual review needed ({best_score}% confidence). Action: Flag for human review"
            else:
                return f"Decision: Low confidence ({best_score}%). Action: Suggest alternatives or request clarification"

        tools.append(make_decision)

        # Document generation tool
        @function_tool(
            name_override="generate_document",
            description_override="Generate quotations, confirmations, or other documents",
        )
        def generate_document(
            doc_type: str, customer_email: str, items: str, decision: str = ""
        ) -> str:
            """Generate business documents"""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            doc_id = datetime.now().strftime("%Y%m%d-%H%M%S")

            if doc_type == "quotation":
                return f"Generated Quotation QUO-{doc_id} for {customer_email}. Items: {items}. Valid for 7 days from {timestamp}"

            elif doc_type == "confirmation":
                return f"Generated Order Confirmation CON-{doc_id} for {customer_email} on {timestamp}. Order: {items}"

            elif doc_type == "clarification":
                return f"Generated Clarification Request CLA-{doc_id} for {customer_email}. Need details about: {items}"

            else:
                return f"Generated {doc_type} document {doc_id} for {customer_email} at {timestamp}"

        tools.append(generate_document)

        # Order status update tool
        @function_tool(
            name_override="update_order_status",
            description_override="Update order status in the system",
        )
        def update_order_status(order_id: str, new_status: str, notes: str = "") -> str:
            """Update order status"""
            valid_statuses = [
                "pending",
                "approved",
                "in_production",
                "completed",
                "cancelled",
            ]

            if new_status not in valid_statuses:
                return f"Error: Invalid status '{new_status}'. Must be one of: {', '.join(valid_statuses)}"

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # In real implementation, would update database
            return f"Order {order_id} status updated to '{new_status}' at {timestamp}. Notes: {notes if notes else 'None'}"

        tools.append(update_order_status)

        return tools

    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Let the agent autonomously process an email with tracing"""
        logger.info(f"Processing email: {email_data.get('subject', 'No subject')}")

        # Create trace name based on email
        trace_name = f"Email_Processing_{email_data.get('subject', 'No_subject')[:30]}"

        # Use trace context for monitoring
        with trace(trace_name):
            try:
                # Construct prompt for autonomous processing
                prompt = f"""
Process this email completely using your available tools:

From: {email_data.get('from', 'Unknown')}
Subject: {email_data.get('subject', 'No subject')}
Body: {email_data.get('body', 'No body')}
Attachments: {len(email_data.get('attachments', []))} files

Steps to follow:
1. Analyze the email to understand its type and intent
2. Extract relevant information based on email type
3. If it's an order, search inventory for matches
4. Retrieve customer context if available
5. Make appropriate decisions
6. Generate necessary documents
7. Update order status if needed

Provide a complete summary of all actions taken and results.
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
                    },
                )

                # Extract tool calls from raw responses
                tool_calls = []
                if hasattr(result, "raw_responses"):
                    for response in result.raw_responses:
                        if hasattr(response, "model_response"):
                            model_resp = response.model_response
                            if hasattr(model_resp, "choices"):
                                for choice in model_resp.choices:
                                    if hasattr(choice, "message") and hasattr(
                                        choice.message, "tool_calls"
                                    ):
                                        if choice.message.tool_calls:
                                            for tc in choice.message.tool_calls:
                                                tool_call = {
                                                    "tool": (
                                                        tc.function.name
                                                        if hasattr(tc.function, "name")
                                                        else "unknown"
                                                    ),
                                                    "args": (
                                                        json.loads(
                                                            tc.function.arguments
                                                        )
                                                        if hasattr(
                                                            tc.function, "arguments"
                                                        )
                                                        else {}
                                                    ),
                                                    "result": "See logs",  # Results aren't directly available
                                                }
                                                tool_calls.append(tool_call)
                                                # Add to trace monitor
                                                trace_monitor.add_tool_call(
                                                    tool_name=tool_call["tool"],
                                                    args=tool_call["args"],
                                                    result=tool_call["result"],
                                                )

                # Log trace information
                logger.info(f"Trace created: {trace_name}")
                logger.info(f"Tool calls made: {len(tool_calls)}")

                # Add decisions to trace monitor
                # Note: RunResult doesn't have context attribute in current SDK
                # if hasattr(result, 'context') and result.context.get('decisions'):
                #     for decision in result.context['decisions']:
                #         trace_monitor.add_decision(
                #             decision_type=decision.get('type', 'unknown'),
                #             details=decision
                #         )

                # End trace with summary
                final_output = str(result) if result else "No output"
                trace_monitor.end_trace("completed", final_output[:200])

                # Extract results
                return {
                    "success": True,
                    "email_id": email_data.get("message_id", "unknown"),
                    "processing_complete": True,
                    "trace_name": trace_name,
                    "tool_calls": tool_calls,
                    "decisions_made": [],  # Would need to extract from tool calls
                    "documents_generated": [],  # Would need to extract from tool calls
                    "final_summary": str(result),
                    "autonomous_actions": len(tool_calls),
                }

            except Exception as e:
                logger.error(f"Error in autonomous processing: {e}")
                return {
                    "success": False,
                    "email_id": email_data.get("message_id", "unknown"),
                    "error": str(e),
                    "trace_name": trace_name,
                }

    async def start_email_monitoring(self):
        """Start autonomous email monitoring with tracing"""
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

    def is_running(self) -> bool:
        """Check if orchestrator is running"""
        return self.is_monitoring

    def _extract_item_description(self, text: str, quantity: str) -> str:
        """Extract item description near quantity mention"""
        # Simple extraction - in real implementation would be more sophisticated
        words = text.split()
        for i, word in enumerate(words):
            if quantity in word:
                start = max(0, i - 5)
                end = min(len(words), i + 5)
                return " ".join(words[start:end])
        return "tags"

    def _extract_specifications(self, text: str) -> Dict[str, Any]:
        """Extract specifications from text"""
        specs = {}

        # Size extraction
        import re

        size_pattern = r"(\d+)\s*x\s*(\d+)\s*(?:inches|inch|cm)?"
        size_match = re.search(size_pattern, text.lower())
        if size_match:
            specs["size"] = f"{size_match.group(1)}x{size_match.group(2)}"

        # Material
        materials = ["cotton", "satin", "leather", "paper", "recycled", "eco"]
        for material in materials:
            if material in text.lower():
                specs["material"] = material
                break

        # Color
        colors = ["black", "white", "blue", "green", "red", "gold", "silver"]
        for color in colors:
            if color in text.lower():
                specs["color"] = color
                break

        return specs
