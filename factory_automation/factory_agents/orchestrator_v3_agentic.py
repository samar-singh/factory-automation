"""True Agentic Orchestrator - Autonomous AI with tool usage"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List

from agents import Agent, Runner, trace, function_tool

from ..factory_config.settings import settings
from ..factory_database.vector_db import ChromaDBClient
from ..factory_utils.trace_monitor import trace_monitor
from .mock_gmail_agent import MockGmailAgent
from .order_processor_agent import OrderProcessorAgent
from .image_processor_agent import ImageProcessorAgent

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
        
        # Initialize new processors
        self.order_processor = OrderProcessorAgent(chromadb_client)
        self.image_processor = ImageProcessorAgent(chromadb_client)

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

        # REMOVED analyze_email - functionality now in process_complete_order

        # Order extraction - kept as internal function, not a tool
        # Use process_complete_order instead for full workflow
        async def _extract_order_items_internal(
            email_body: str, has_attachments: bool = False
        ) -> str:
            """Internal function to extract order items using OpenAI GPT-4"""
            from openai import AsyncOpenAI
            import re
            
            # Initialize OpenAI client
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            
            # Prepare the prompt for GPT-4
            extraction_prompt = f"""
            You are an expert at extracting order information from emails for a garment price tag manufacturing factory.
            
            Analyze the following email and extract ALL order items with their specifications.
            
            Email Content:
            {email_body}
            
            Extract the following information for EACH item ordered:
            1. Item type (e.g., price tags, hang tags, care labels, barcode stickers, etc.)
            2. Quantity (number of pieces/units)
            3. Brand/Customer name
            4. Color specifications if mentioned
            5. Size specifications (dimensions if provided)
            6. Material type if mentioned (paper, plastic, fabric, etc.)
            7. Special requirements (printing, embossing, special finishes)
            8. Any product codes or SKUs mentioned
            9. Delivery timeline if mentioned
            
            IMPORTANT:
            - Extract ALL items mentioned, even if details are incomplete
            - If quantity is mentioned as "tags for X items", calculate the actual tag quantity
            - Look for both explicit orders and implied requirements
            - Note any references to attachments that might contain additional details
            
            Return the extracted information as a JSON object with this structure:
            {{
                "customer_name": "extracted customer/brand name",
                "order_items": [
                    {{
                        "item_type": "type of tag/label",
                        "quantity": number,
                        "brand": "brand name if different from customer",
                        "color": "color if specified",
                        "size": "dimensions if specified",
                        "material": "material type",
                        "special_requirements": ["list of special requirements"],
                        "product_code": "code if mentioned",
                        "description": "full description combining all details"
                    }}
                ],
                "delivery_timeline": "urgency or deadline if mentioned",
                "additional_notes": "any other important information",
                "confidence_level": "high/medium/low based on clarity of requirements",
                "missing_information": ["list of important missing details"]
            }}
            
            If no clear order items can be extracted, return an appropriate message explaining what information is needed.
            """
            
            try:
                # Call GPT-4 for intelligent extraction
                response = await client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert at extracting structured order information from unstructured text. Always return valid JSON."
                        },
                        {
                            "role": "user",
                            "content": extraction_prompt
                        }
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,  # Low temperature for consistent extraction
                    max_tokens=2000
                )
                
                # Parse the AI response
                extracted_data = json.loads(response.choices[0].message.content)
                
                # Add metadata
                extracted_data["extraction_method"] = "ai_gpt4"
                extracted_data["has_attachments"] = has_attachments
                extracted_data["extraction_timestamp"] = datetime.now().isoformat()
                
                # Enhance with basic pattern matching as fallback
                if not extracted_data.get("order_items") or len(extracted_data["order_items"]) == 0:
                    # Fallback to basic pattern matching
                    items = []
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
                            
                            items.append({
                                "quantity": int(qty),
                                "description": f"Extracted quantity: {qty}",
                                "item_type": "price_tag",  # Default assumption
                                "extraction_method": "pattern_matching"
                            })
                    
                    if items:
                        extracted_data["order_items"] = items
                        extracted_data["confidence_level"] = "low"
                        extracted_data["extraction_method"] = "hybrid_ai_pattern"
                
                # Log successful extraction
                logger.info(f"AI extracted {len(extracted_data.get('order_items', []))} items from email")
                
                return json.dumps(extracted_data, indent=2)
                
            except Exception as e:
                logger.error(f"AI extraction failed: {str(e)}, falling back to basic extraction")
                
                # Fallback to basic extraction
                items = []
                import re
                
                # Basic pattern matching
                quantity_patterns = [
                    r"(\d+)\s*(pcs|pieces|units|nos|tags)",
                    r"quantity[:\s]+(\d+)",
                ]
                
                for pattern in quantity_patterns:
                    matches = re.findall(pattern, email_body.lower())
                    for match in matches:
                        if isinstance(match, tuple):
                            qty = match[0]
                            unit = match[1] if len(match) > 1 else "units"
                        else:
                            qty = match
                            unit = "units"
                        
                        items.append({
                            "quantity": int(qty),
                            "unit": unit,
                            "description": f"{qty} {unit} extracted via pattern matching",
                            "item_type": "unknown",
                            "extraction_method": "fallback_pattern"
                        })
                
                return json.dumps({
                    "items": items,
                    "extraction_method": "fallback",
                    "error": str(e),
                    "total_items": len(items),
                    "requires_clarification": True,
                    "confidence_level": "low"
                })

        # NOT adding extract_order_items as tool - use process_complete_order instead

        # Complete order processing tool with full workflow
        @function_tool(
            name_override="process_complete_order",
            description_override="Process complete order with attachments, ChromaDB search, and human review workflow"
        )
        async def process_complete_order(
            email_subject: str,
            email_body: str,
            sender_email: str
        ) -> str:
            """Process complete order using OrderProcessorAgent"""
            try:
                # Use the OrderProcessorAgent for comprehensive processing
                result = await self.order_processor.process_order_email(
                    email_subject=email_subject,
                    email_body=email_body,
                    email_date=datetime.now(),
                    sender_email=sender_email,
                    attachments=[]  # Empty for now, can be extended later
                )
                
                # Format response
                response = {
                    "order_id": result.order.order_id if result.order else "N/A",
                    "customer": result.order.customer.company_name if result.order else "Unknown",
                    "total_items": len(result.order.items) if result.order else 0,
                    "extraction_confidence": result.order.extraction_confidence if result.order else 0,
                    "recommended_action": result.recommended_action,
                    "approval_status": result.order.approval_status if result.order else "failed",
                    "inventory_matches": len(result.inventory_matches),
                    "processing_time_ms": result.processing_time_ms,
                    "items": []
                }
                
                # Add item details
                if result.order:
                    for item in result.order.items[:5]:  # Limit to first 5 items
                        response["items"].append({
                            "tag_code": item.tag_specification.tag_code,
                            "quantity": item.quantity_ordered,
                            "brand": item.brand,
                            "match_score": item.inventory_match_score or 0
                        })
                
                # Add any errors or warnings
                if result.errors:
                    response["errors"] = result.errors
                if result.warnings:
                    response["warnings"] = result.warnings
                
                logger.info(f"Processed complete order {response['order_id']} with action: {response['recommended_action']}")
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error in process_complete_order: {e}")
                return json.dumps({
                    "error": str(e),
                    "status": "failed"
                })
        
        tools.append(process_complete_order)

        # Process image attachments tool
        @function_tool(
            name_override="process_tag_image",
            description_override="Process tag image with Qwen2.5VL and store in ChromaDB"
        )
        async def process_tag_image(
            image_path: str,
            order_id: str,
            customer_name: str
        ) -> str:
            """Process and analyze tag image"""
            try:
                result = await self.image_processor.process_and_store_image(
                    image_path=image_path,
                    order_id=order_id,
                    customer_name=customer_name
                )
                
                response = {
                    "status": result.get("status"),
                    "image_hash": result.get("image_hash"),
                    "tag_type": result.get("analysis", {}).get("tag_type"),
                    "brand": result.get("analysis", {}).get("brand"),
                    "text_content": result.get("analysis", {}).get("text_content"),
                    "colors": result.get("analysis", {}).get("colors"),
                    "stored_in_chromadb": result.get("status") == "success"
                }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error processing tag image: {e}")
                return json.dumps({"error": str(e), "status": "failed"})
        
        tools.append(process_tag_image)

        # Inventory search tool
        @function_tool(
            name_override="search_inventory",
            description_override="Search inventory using semantic similarity in ChromaDB",
        )
        def search_inventory(
            query: str,
            min_quantity: int = 0,
            limit: int = 5
        ) -> str:
            """Search ChromaDB for matching inventory"""
            try:
                # Build metadata filter
                where = {}
                # Removed brand_filter since it's not in the function signature
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

                return json.dumps(matches, indent=2)
            except Exception as e:
                logger.error(f"Error searching inventory: {e}")
                return json.dumps({"error": str(e), "matches": []})

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

        # REMOVED make_decision - this logic is now in process_complete_order
        # Decision thresholds: >80% auto-approve, 60-80% human review, <60% clarification

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
