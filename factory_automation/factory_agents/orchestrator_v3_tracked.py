"""Agentic Orchestrator with explicit tool call tracking"""

import logging
from datetime import datetime
from typing import Any, Dict
from functools import wraps

from agents import Agent, Runner, function_tool

from ..factory_database.vector_db import ChromaDBClient
from ..factory_utils.trace_monitor import trace_monitor
from .mock_gmail_agent import MockGmailAgent

logger = logging.getLogger(__name__)


class TrackedOrchestratorV3:
    """Orchestrator with explicit tool call tracking"""

    def __init__(self, chromadb_client: ChromaDBClient):
        self.chromadb_client = chromadb_client
        self.runner = Runner()
        self.gmail_agent = MockGmailAgent()
        self.gmail_agent.initialize_service("factory@example.com")

        # Tool call tracking
        self.current_trace_tools = []

        # Create tools with tracking
        self.tools = self._create_tracked_tools()

        # Create agent
        self.agent = Agent(
            name="TrackedOrchestrator",
            instructions="""You are a factory automation orchestrator. Process emails by:
1. Analyzing the email type and urgency
2. Extracting order details if it's an order
3. Searching inventory for matches
4. Making approval decisions
5. Generating appropriate documents

Use your tools step by step.""",
            tools=self.tools,
            model="gpt-4o",
        )

        logger.info(f"Initialized Tracked Orchestrator with {len(self.tools)} tools")

    def _track_call(self, tool_name: str):
        """Decorator to track tool calls"""

        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Track the call
                call_info = {
                    "tool": tool_name,
                    "args": {"args": args, "kwargs": kwargs},
                    "timestamp": datetime.now().isoformat(),
                }

                try:
                    # Execute the tool
                    result = func(*args, **kwargs)
                    call_info["result"] = str(result)[:200]  # Truncate for storage
                    call_info["success"] = True
                except Exception as e:
                    call_info["result"] = f"Error: {str(e)}"
                    call_info["success"] = False
                    result = f"Error in {tool_name}: {str(e)}"

                # Add to current trace
                self.current_trace_tools.append(call_info)
                logger.info(
                    f"Tool called: {tool_name} (Total calls: {len(self.current_trace_tools)})"
                )

                return result

            return wrapper

        return decorator

    def _create_tracked_tools(self):
        """Create tools with call tracking"""
        tools = []

        # Analyze email
        @function_tool
        def analyze_email(subject: str, body: str, from_email: str) -> str:
            """Analyze email to determine type and urgency"""
            # Track this call
            self.current_trace_tools.append(
                {
                    "tool": "analyze_email",
                    "args": {"subject": subject, "from": from_email},
                    "timestamp": datetime.now().isoformat(),
                }
            )

            body_lower = body.lower()

            # Determine type
            if any(word in body_lower for word in ["order", "need", "require"]):
                email_type = "order"
            elif any(word in body_lower for word in ["payment", "paid", "utr"]):
                email_type = "payment"
            else:
                email_type = "query"

            # Check urgency
            is_urgent = "urgent" in body_lower or "asap" in body_lower

            result = f"Type: {email_type}, Urgent: {is_urgent}"
            self.current_trace_tools[-1]["result"] = result

            logger.info(f"analyze_email called - {result}")
            return result

        tools.append(analyze_email)

        # Extract order items - AI-powered
        @function_tool
        def extract_order_items(email_body: str) -> str:
            """Extract order details from email using AI"""
            # Track this call
            self.current_trace_tools.append(
                {
                    "tool": "extract_order_items",
                    "args": {"body_length": len(email_body)},
                    "timestamp": datetime.now().isoformat(),
                }
            )

            from openai import OpenAI
            import re
            import json
            
            # Initialize OpenAI client synchronously
            client = OpenAI(api_key=settings.openai_api_key)
            
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
            
            Return as JSON with this structure:
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
                "confidence_level": "high/medium/low based on clarity of requirements"
            }}
            """
            
            try:
                # Call GPT-4 for intelligent extraction
                response = client.chat.completions.create(
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
                    temperature=0.1,
                    max_tokens=2000
                )
                
                # Parse the AI response
                extracted_data = json.loads(response.choices[0].message.content)
                
                # Add metadata
                extracted_data["extraction_method"] = "ai_gpt4"
                extracted_data["extraction_timestamp"] = datetime.now().isoformat()
                
                # Log successful extraction
                logger.info(f"AI extracted {len(extracted_data.get('order_items', []))} items from email")
                
                result = json.dumps(extracted_data, indent=2)
                
            except Exception as e:
                logger.error(f"AI extraction failed: {str(e)}, falling back to basic extraction")
                
                # Fallback to basic pattern matching
                body_lower = email_body.lower()
                
                # Extract quantities
                quantities = re.findall(r"(\d+)\s*(?:pcs|pieces|tags|units)?", body_lower)
                
                # Extract colors
                colors = []
                for color in ["black", "red", "blue", "green", "white", "silver"]:
                    if color in body_lower:
                        colors.append(color)
                
                # Extract item types
                items = []
                if "tag" in body_lower:
                    items.append("tags")
                if "label" in body_lower:
                    items.append("labels")

            if quantities and (colors or items):
                qty = quantities[0]
                color = colors[0] if colors else ""
                item = items[0] if items else "items"
                result = f"Extracted: {qty} x {color} {item}"
            else:
                result = "No specific items extracted"

            self.current_trace_tools[-1]["result"] = result
            logger.info(f"extract_order_items called - {result}")
            return result

        tools.append(extract_order_items)

        # Search inventory
        @function_tool
        def search_inventory(query: str) -> str:
            """Search inventory for matching items"""
            # Track this call
            self.current_trace_tools.append(
                {
                    "tool": "search_inventory",
                    "args": {"query": query},
                    "timestamp": datetime.now().isoformat(),
                }
            )

            try:
                results = self.chromadb_client.search(query, n_results=5)

                if results and results.get("documents") and results["documents"][0]:
                    matches = []
                    for i, (doc, dist) in enumerate(
                        zip(results["documents"][0][:3], results["distances"][0][:3]), 1
                    ):
                        score = max(0, 1 - (dist / 2))
                        matches.append(f"{doc[:30]}... ({score:.0%} match)")

                    result = (
                        f"Found {len(results['documents'][0])} matches: "
                        + "; ".join(matches)
                    )
                else:
                    result = f"No matches found for: {query}"

            except Exception as e:
                logger.error(f"Search error: {e}")
                result = f"Search failed: {str(e)}"

            self.current_trace_tools[-1]["result"] = result
            logger.info(f"search_inventory called - {result[:100]}...")
            return result

        tools.append(search_inventory)

        # Make decision
        @function_tool
        def make_decision(search_results: str, urgency: bool = False) -> str:
            """Make approval decision based on search results"""
            # Track this call
            self.current_trace_tools.append(
                {
                    "tool": "make_decision",
                    "args": {"urgency": urgency},
                    "timestamp": datetime.now().isoformat(),
                }
            )

            if "No matches found" in search_results:
                result = "Decision: No matches - request clarification"
            else:
                # Extract scores
                import re

                scores = re.findall(r"(\d+)% match", search_results)

                if scores:
                    best_score = max(int(s) for s in scores)

                    if best_score > 80:
                        result = f"Decision: Auto-approved ({best_score}% confidence)"
                    elif best_score > 60:
                        result = (
                            f"Decision: Manual review needed ({best_score}% confidence)"
                        )
                    else:
                        result = f"Decision: Low confidence ({best_score}%) - suggest alternatives"
                else:
                    result = "Decision: Unable to determine - needs manual review"

            self.current_trace_tools[-1]["result"] = result
            logger.info(f"make_decision called - {result}")
            return result

        tools.append(make_decision)

        return tools

    async def process_email(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process email with tool tracking"""
        logger.info(f"Processing email: {email_data.get('subject', 'No subject')}")

        # Reset tool tracking for this trace
        self.current_trace_tools = []

        # Create trace
        trace_name = f"Email_{email_data.get('subject', 'unknown')[:20]}"
        trace_monitor.start_trace(trace_name)

        try:
            # Build prompt
            prompt = f"""Process this email step by step:
From: {email_data.get('from', 'Unknown')}
Subject: {email_data.get('subject', 'No subject')}
Body: {email_data.get('body', 'No body')}

Use your tools to analyze, extract, search, and make decisions."""

            # Run agent
            result = await self.runner.run(self.agent, prompt)

            # Get tracked tool calls
            tool_calls = self.current_trace_tools.copy()

            logger.info(f"Processing complete. Tools used: {len(tool_calls)}")

            # Add to trace monitor
            for call in tool_calls:
                trace_monitor.add_tool_call(
                    tool_name=call["tool"],
                    args=call.get("args", {}),
                    result=call.get("result", "No result"),
                )

            trace_monitor.end_trace("completed")

            return {
                "success": True,
                "tool_calls": tool_calls,
                "autonomous_actions": len(tool_calls),
                "final_summary": str(result),
                "trace_name": trace_name,
            }

        except Exception as e:
            logger.error(f"Processing error: {e}")
            trace_monitor.add_error(str(e))
            trace_monitor.end_trace("failed")

            return {
                "success": False,
                "error": str(e),
                "tool_calls": self.current_trace_tools,
                "trace_name": trace_name,
            }
