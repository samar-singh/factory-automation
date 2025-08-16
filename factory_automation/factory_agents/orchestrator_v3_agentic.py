"""True Agentic Orchestrator - Autonomous AI with tool usage"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents import Agent, Runner, function_tool, trace

from ..factory_config.settings import settings
from ..factory_database.vector_db import ChromaDBClient
from ..factory_utils.trace_monitor import trace_monitor
from .image_processor_agent import ImageProcessorAgent
from .mock_gmail_agent import MockGmailAgent
from .order_processor_agent import OrderProcessorAgent

logger = logging.getLogger(__name__)


class AgenticOrchestratorV3:
    """Fully autonomous orchestrator using OpenAI Agents SDK with callable tools"""

    def __init__(self, chromadb_client: ChromaDBClient, use_mock_gmail: bool = True):
        """Initialize with ChromaDB and create autonomous agent"""
        self.chromadb_client = chromadb_client
        self.runner = Runner()
        self.is_monitoring = False

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
            if not self.gmail_agent:
                logger.debug("Gmail agent disabled - no emails to check")
                return []

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

        # Email classification tool - MUST be used first for every email
        @function_tool(
            name_override="classify_email_intent",
            description_override="Intelligently classify email intent using business context, patterns, and AI. ALWAYS use this FIRST before any other processing.",
        )
        async def classify_email_intent(
            email_subject: str,
            email_body: str,
            sender_email: str,
            recipient_email: Optional[str] = None,
        ) -> str:
            """Classify email using business context, patterns, and GPT-4o"""
            import json

            from ..factory_database.connection import get_db
            from ..factory_database.models import EmailPattern

            # Normalize recipient email
            if recipient_email:
                recipient_email = recipient_email.lower()
            else:
                recipient_email = (
                    self.primary_emails[0]
                    if self.primary_emails
                    else "orders@factory.com"
                )

            # Get the business context for this email
            email_config = self.email_configs.get(recipient_email, {})
            email_description = email_config.get(
                "description", "General business email"
            )
            likely_intents = email_config.get("likely_intents", [])
            confidence_boost = email_config.get("confidence_boost", 0.0)

            # Step 1: Check sender pattern in PostgreSQL
            if self.pattern_config.get("enabled", True):
                try:
                    with get_db() as db:
                        pattern = (
                            db.query(EmailPattern)
                            .filter(
                                EmailPattern.sender_email == sender_email,
                                EmailPattern.recipient_email == recipient_email,
                            )
                            .order_by(EmailPattern.count.desc())
                            .first()
                        )

                        min_count = self.pattern_config.get("min_count_for_pattern", 3)

                        if pattern and pattern.count >= min_count:
                            # Calculate confidence
                            base_confidence = self.pattern_config.get(
                                "initial_confidence", 0.6
                            )
                            increment = self.pattern_config.get(
                                "confidence_increment", 0.05
                            )
                            max_conf = self.pattern_config.get("max_confidence", 0.95)

                            confidence = min(
                                max_conf, base_confidence + (pattern.count * increment)
                            )

                            # Apply boost if this intent is likely for this email
                            if pattern.intent_type in likely_intents:
                                confidence = min(
                                    max_conf, confidence + confidence_boost
                                )

                            if confidence > 0.85:
                                logger.info(
                                    f"Using learned pattern for {sender_email}→{recipient_email}: {pattern.intent_type}"
                                )
                                return json.dumps(
                                    {
                                        "classification": pattern.intent_type,
                                        "confidence": confidence,
                                        "method": "learned_pattern",
                                        "pattern_count": pattern.count,
                                        "recipient_email": recipient_email,
                                        "recipient_description": email_description,
                                        "suggested_tools": self._get_tools_for_intent(
                                            pattern.intent_type
                                        ),
                                    }
                                )
                except Exception as e:
                    logger.warning(f"Error checking patterns: {e}")

            # Step 2: Use GPT-4o with full business context
            try:
                # Build context-rich prompt
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": f"""You are classifying emails for a garment tag manufacturing factory.
                            
                            CRITICAL CONTEXT - This email was sent to: {recipient_email}
                            
                            PURPOSE OF THIS EMAIL ADDRESS:
                            {email_description}
                            
                            EXPECTED EMAIL TYPES for {recipient_email}:
                            {', '.join(likely_intents) if likely_intents else 'Various business communications'}
                            
                            ALL POSSIBLE CLASSIFICATIONS:
                            - NEW_ORDER: Customer placing an order for tags/labels
                            - ORDER_MODIFICATION: Changes to existing order
                            - URGENT_ORDER: Rush/priority order requests
                            - PAYMENT: Payment confirmations, UTR numbers
                            - PAYMENT_INQUIRY: Questions about payment status
                            - INQUIRY: General questions about products/services
                            - QUOTATION_REQUEST: Request for price quotes
                            - NEW_CUSTOMER: New customer onboarding
                            - FOLLOWUP: Status check on existing order
                            - SUPPLIER: Vendor/supplier communications
                            - MATERIAL_QUOTATION: Raw material pricing from suppliers
                            - DELIVERY_UPDATE: Shipping/delivery information
                            - COMPLAINT: Issues with products/service
                            - QUALITY_ISSUE: Specific quality problems
                            - INVOICE_REQUEST: Request for invoice/billing documents
                            
                            Consider the email address purpose when classifying. For example:
                            - If sent to orders@: likely NEW_ORDER unless clearly otherwise
                            - If sent to sales@: likely INQUIRY or QUOTATION_REQUEST
                            - If sent to info@: could be various types
                            
                            Return JSON with:
                            - classification: The most appropriate intent type
                            - confidence: 0.0 to 1.0 (consider email address context)
                            - reasoning: Why you chose this classification
                            - key_indicators: Specific words/phrases that guided your decision
                            - alternative_classification: Second most likely intent (if any)
                            - extracted_entities: Order numbers, UTRs, quantities, etc.
                            """,
                        },
                        {
                            "role": "user",
                            "content": f"""
                            Email Details:
                            To: {recipient_email} ({email_description[:100]})
                            From: {sender_email}
                            Subject: {email_subject}
                            Body: {email_body[:1000]}
                            
                            Classify this email considering it was sent to an address meant for: {email_description}
                            """,
                        },
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                )

                result = json.loads(response.choices[0].message.content)

                # Apply confidence boost if classification matches expected intent
                if result["classification"] in likely_intents:
                    original_confidence = result["confidence"]
                    result["confidence"] = min(
                        0.99, result["confidence"] + confidence_boost
                    )
                    result["confidence_boosted"] = True
                    result["boost_reason"] = (
                        f"Matches expected intent for {recipient_email}"
                    )
                    logger.info(
                        f"Boosted confidence from {original_confidence:.2f} to {result['confidence']:.2f}"
                    )

                # Store pattern for learning with description
                if self.pattern_config.get("enabled", True):
                    await self._update_sender_pattern(
                        sender_email,
                        recipient_email,
                        email_description,
                        result["classification"],
                        email_subject,
                    )

                result["method"] = "ai_analysis_with_context"
                result["recipient_email"] = recipient_email
                result["recipient_description"] = email_description
                result["suggested_tools"] = self._get_tools_for_intent(
                    result["classification"]
                )

                return json.dumps(result)

            except Exception as e:
                logger.error(f"AI classification failed: {e}")
                # Context-aware fallback
                default_intent = likely_intents[0] if likely_intents else "NEW_ORDER"
                return json.dumps(
                    {
                        "classification": default_intent,
                        "confidence": 0.4,
                        "error": str(e),
                        "method": "context_aware_fallback",
                        "recipient_email": recipient_email,
                        "recipient_description": email_description,
                        "fallback_reason": f"Using most likely intent for {recipient_email}",
                        "suggested_tools": self._get_tools_for_intent(default_intent),
                    }
                )

        tools.append(classify_email_intent)

        # REMOVED analyze_email - functionality now in process_complete_order

        # Order extraction - kept as internal function, not a tool
        # Use process_complete_order instead for full workflow
        async def _extract_order_items_internal(
            email_body: str, has_attachments: bool = False
        ) -> str:
            """Internal function to extract order items using OpenAI GPT-4"""
            import re

            from openai import AsyncOpenAI

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
                            "content": "You are an expert at extracting structured order information from unstructured text. Always return valid JSON.",
                        },
                        {"role": "user", "content": extraction_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,  # Low temperature for consistent extraction
                    max_tokens=2000,
                )

                # Parse the AI response
                extracted_data = json.loads(response.choices[0].message.content)

                # Add metadata
                extracted_data["extraction_method"] = "ai_gpt4"
                extracted_data["has_attachments"] = has_attachments
                extracted_data["extraction_timestamp"] = datetime.now().isoformat()

                # Enhance with basic pattern matching as fallback
                if (
                    not extracted_data.get("order_items")
                    or len(extracted_data["order_items"]) == 0
                ):
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

                            items.append(
                                {
                                    "quantity": int(qty),
                                    "description": f"Extracted quantity: {qty}",
                                    "item_type": "price_tag",  # Default assumption
                                    "extraction_method": "pattern_matching",
                                }
                            )

                    if items:
                        extracted_data["order_items"] = items
                        extracted_data["confidence_level"] = "low"
                        extracted_data["extraction_method"] = "hybrid_ai_pattern"

                # Log successful extraction
                logger.info(
                    f"AI extracted {len(extracted_data.get('order_items', []))} items from email"
                )

                return json.dumps(extracted_data, indent=2)

            except Exception as e:
                logger.error(
                    f"AI extraction failed: {str(e)}, falling back to basic extraction"
                )

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

                        items.append(
                            {
                                "quantity": int(qty),
                                "unit": unit,
                                "description": f"{qty} {unit} extracted via pattern matching",
                                "item_type": "unknown",
                                "extraction_method": "fallback_pattern",
                            }
                        )

                return json.dumps(
                    {
                        "items": items,
                        "extraction_method": "fallback",
                        "error": str(e),
                        "total_items": len(items),
                        "requires_clarification": True,
                        "confidence_level": "low",
                    }
                )

        # NOT adding extract_order_items as tool - use process_complete_order instead

        # Track processed emails to prevent duplicates
        self._processed_emails = set()
        self._current_attachments = []  # Store current email attachments
        self._last_order_result = None  # Store the last order processing result

        # Complete order processing tool with full workflow
        @function_tool(
            name_override="process_complete_order",
            description_override="Process complete order with attachments, ChromaDB search, and human review workflow. Attachments are automatically retrieved from context.",
        )
        async def process_complete_order(
            email_subject: str,
            email_body: str,
            sender_email: str,
            attachments: Optional[str] = None,
        ) -> str:
            """Process complete order using OrderProcessorAgent with attachment support"""

            # Create a unique key for this email
            email_key = f"{sender_email}:{email_subject}"

            # Check if already processed
            if email_key in self._processed_emails:
                logger.warning(f"Email already processed: {email_key}")
                return json.dumps(
                    {
                        "status": "duplicate",
                        "message": "This email has already been processed",
                        "email_subject": email_subject,
                        "sender": sender_email,
                    }
                )

            # Mark as processed
            self._processed_emails.add(email_key)

            try:
                # Always use attachments from context (they contain file paths)
                attachment_list = []
                if hasattr(self, "_current_attachments") and self._current_attachments:
                    attachment_list = self._current_attachments
                    logger.info(
                        f"Using {len(attachment_list)} attachments from context"
                    )
                    for att in attachment_list:
                        logger.debug(
                            f"  - {att.get('filename')}: {att.get('filepath')}"
                        )
                else:
                    logger.info("No attachments in context")

                # If attachments were explicitly passed (shouldn't happen with new design)
                if attachments and not attachment_list:
                    logger.warning("Attachments passed as parameter (legacy behavior)")
                    try:
                        if isinstance(attachments, str):
                            attachment_list = json.loads(attachments)
                        else:
                            attachment_list = attachments
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse attachments JSON: {attachments}")

                # Use the OrderProcessorAgent for comprehensive processing
                result = await self.order_processor.process_order_email(
                    email_subject=email_subject,
                    email_body=email_body,
                    email_date=datetime.now(),
                    sender_email=sender_email,
                    attachments=attachment_list,  # Pass parsed attachments
                )

                # Format response
                response = {
                    "order_id": result.order.order_id if result.order else "N/A",
                    "customer": (
                        result.order.customer.company_name
                        if result.order
                        else "Unknown"
                    ),
                    "total_items": len(result.order.items) if result.order else 0,
                    "extraction_confidence": (
                        result.order.extraction_confidence if result.order else 0
                    ),
                    "recommended_action": result.recommended_action,
                    "approval_status": (
                        result.order.approval_status if result.order else "failed"
                    ),
                    "inventory_matches": (
                        result.inventory_matches[:20]
                        if result.inventory_matches
                        else []
                    ),  # Keep actual matches for review
                    "image_matches": (
                        len(result.image_matches)
                        if hasattr(result, "image_matches")
                        else 0
                    ),
                    "processing_time_ms": result.processing_time_ms,
                    "items": [],
                    "confidence_scores": (
                        result.confidence_scores
                        if hasattr(result, "confidence_scores")
                        else {}
                    ),
                }

                # Add item details with image match info
                if result.order:
                    for item in result.order.items[:5]:  # Limit to first 5 items
                        item_data = {
                            "tag_code": item.tag_specification.tag_code,
                            "quantity": item.quantity_ordered,
                            "brand": item.brand,
                            "match_score": item.inventory_match_score or 0,
                        }
                        # Add best image match if available
                        if hasattr(item, "best_image_match") and item.best_image_match:
                            item_data["best_image_match"] = {
                                "tag_code": item.best_image_match.get(
                                    "tag_code", "Unknown"
                                ),
                                "confidence": item.best_image_match.get(
                                    "confidence", 0
                                ),
                                "has_image": "image_path" in item.best_image_match,
                            }
                        response["items"].append(item_data)

                # Add any errors or warnings
                if result.errors:
                    response["errors"] = result.errors
                if result.warnings:
                    response["warnings"] = result.warnings

                logger.info(
                    f"Processed complete order {response['order_id']} with action: {response['recommended_action']}"
                )

                # DO NOT auto-create review here - let the orchestrator AI decide
                # The orchestrator AI will use the create_human_review tool if needed
                if result.recommended_action == "human_review":
                    response["needs_review"] = True
                    response["review_reason"] = getattr(
                        result.order, "review_notes", "Manual review required"
                    )

                    # Prepare data for AI to use in review creation
                    response["review_data_prepared"] = True

                    # Add extracted items for review
                    extracted_items = []
                    if result.order and result.order.items:
                        for item in result.order.items:
                            extracted_items.append(
                                {
                                    "tag_code": item.tag_specification.tag_code,
                                    "tag_type": item.tag_specification.tag_type.value,
                                    "quantity": item.quantity_ordered,
                                    "brand": item.brand,
                                    "match_score": item.inventory_match_score or 0,
                                }
                            )
                    response["extracted_items_for_review"] = extracted_items

                    logger.info(
                        f"Order {response['order_id']} marked for review - orchestrator AI will decide on creation"
                    )

                # Store the result for the AI to use when creating review
                if hasattr(self, "human_manager"):
                    # Store in the orchestrator that has human_manager
                    self._last_order_result = response
                    self._current_email_subject = email_subject
                    self._current_email_body = email_body

                # Store the actual image matches list if available
                if hasattr(result, "image_matches") and isinstance(
                    result.image_matches, list
                ):
                    response["image_matches_list"] = result.image_matches
                    logger.info(
                        f"Added {len(result.image_matches)} image matches to response"
                    )

                # Store the result for GUI access
                self._last_order_result = response
                return json.dumps(response, indent=2)

            except Exception as e:
                logger.error(f"Error in process_complete_order: {e}")
                return json.dumps({"error": str(e), "status": "failed"})

        tools.append(process_complete_order)

        # Extract data from Excel attachment
        @function_tool(
            name_override="extract_excel_data",
            description_override="Extract order data from Excel file attachment",
        )
        async def extract_excel_data(filename: str, content: str) -> str:
            """Extract and parse data from Excel attachment"""
            try:
                import base64
                import tempfile
                from pathlib import Path

                import pandas as pd

                # Decode base64 content if needed
                if isinstance(content, str):
                    content_bytes = base64.b64decode(content)
                else:
                    content_bytes = content

                # Save temporarily and read with pandas
                with tempfile.NamedTemporaryFile(
                    suffix=".xlsx", delete=False
                ) as tmp_file:
                    tmp_file.write(content_bytes)
                    tmp_path = tmp_file.name

                # Read Excel file
                df = pd.read_excel(tmp_path)

                # Extract relevant data
                extracted_data = {
                    "filename": filename,
                    "rows": len(df),
                    "columns": list(df.columns),
                    "sample_data": df.head(10).to_dict(orient="records"),
                    "summary": f"Excel file with {len(df)} rows and {len(df.columns)} columns",
                }

                # Clean up
                Path(tmp_path).unlink()

                logger.info(f"Extracted data from Excel: {filename}")
                return json.dumps(extracted_data, indent=2)

            except Exception as e:
                logger.error(f"Error extracting Excel data: {e}")
                return json.dumps({"error": str(e), "filename": filename})

        tools.append(extract_excel_data)

        # Extract data from PDF attachment
        @function_tool(
            name_override="extract_pdf_data",
            description_override="Extract text content from PDF attachment",
        )
        async def extract_pdf_data(filename: str, content: str) -> str:
            """Extract text from PDF attachment"""
            try:
                import base64
                import tempfile
                from pathlib import Path

                import PyPDF2

                # Decode base64 content if needed
                if isinstance(content, str):
                    content_bytes = base64.b64decode(content)
                else:
                    content_bytes = content

                # Save temporarily
                with tempfile.NamedTemporaryFile(
                    suffix=".pdf", delete=False
                ) as tmp_file:
                    tmp_file.write(content_bytes)
                    tmp_path = tmp_file.name

                # Read PDF
                with open(tmp_path, "rb") as pdf_file:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    num_pages = len(pdf_reader.pages)

                    # Extract text from all pages
                    extracted_text = []
                    for page_num in range(
                        min(num_pages, 10)
                    ):  # Limit to first 10 pages
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        if text:
                            extracted_text.append(f"Page {page_num + 1}:\n{text}")

                # Clean up
                Path(tmp_path).unlink()

                result = {
                    "filename": filename,
                    "pages": num_pages,
                    "extracted_text": "\n\n".join(extracted_text),
                    "summary": f"PDF with {num_pages} pages",
                }

                logger.info(f"Extracted text from PDF: {filename}")
                return json.dumps(result, indent=2)

            except Exception as e:
                logger.error(f"Error extracting PDF data: {e}")
                return json.dumps({"error": str(e), "filename": filename})

        tools.append(extract_pdf_data)

        # Process image attachments tool
        @function_tool(
            name_override="process_tag_image",
            description_override="Process tag image with Qwen2.5VL and store in ChromaDB",
        )
        async def process_tag_image(
            image_path: str, order_id: str, customer_name: str
        ) -> str:
            """Process and analyze tag image"""
            try:
                result = await self.image_processor.process_and_store_image(
                    image_path=image_path,
                    order_id=order_id,
                    customer_name=customer_name,
                )

                response = {
                    "status": result.get("status"),
                    "image_hash": result.get("image_hash"),
                    "tag_type": result.get("analysis", {}).get("tag_type"),
                    "brand": result.get("analysis", {}).get("brand"),
                    "text_content": result.get("analysis", {}).get("text_content"),
                    "colors": result.get("analysis", {}).get("colors"),
                    "stored_in_chromadb": result.get("status") == "success",
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
        def search_inventory(query: str, min_quantity: int = 0, limit: int = 5) -> str:
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

        # Email response tool - Send automated responses to customers/suppliers
        @function_tool(
            name_override="send_email_response",
            description_override="Send email responses to customers, suppliers, or internal staff. Use this to complete the communication loop after processing.",
        )
        async def send_email_response(
            to_email: str,
            subject: str,
            body: str,
            email_type: str,
            attachments: Optional[List[str]] = None,
        ) -> str:
            """Send email response"""
            import json

            try:
                # Check if we have Gmail production agent with sending capability
                if hasattr(self, "gmail_agent") and self.gmail_agent:
                    # TODO: Implement actual Gmail sending when API is configured
                    # For now, return mock successful response
                    logger.info(f"Sending {email_type} email to {to_email}")
                    logger.debug(
                        f"Email content: Subject: {subject}, Body preview: {body[:200]}..."
                    )

                    result = {
                        "email_sent": True,
                        "to": to_email,
                        "subject": subject,
                        "type": email_type,
                        "has_attachments": bool(attachments),
                        "timestamp": datetime.now().isoformat(),
                        "status": "sent_successfully",
                        "mock_mode": True,  # Remove when actual sending is implemented
                    }

                    # Log the response for tracking
                    logger.info(f"Email response sent successfully to {to_email}")

                    return json.dumps(result)
                else:
                    # No Gmail agent available
                    logger.warning("Gmail agent not available for sending emails")

                    result = {
                        "email_sent": False,
                        "to": to_email,
                        "subject": subject,
                        "type": email_type,
                        "status": "gmail_not_configured",
                        "message": "Email queued for sending when Gmail is configured",
                    }

                    return json.dumps(result)

            except Exception as e:
                logger.error(f"Error sending email response: {e}")
                return json.dumps(
                    {
                        "email_sent": False,
                        "error": str(e),
                        "to": to_email,
                        "subject": subject,
                    }
                )

        tools.append(send_email_response)

        # Payment tracking tool - Process payment confirmations
        @function_tool(
            name_override="track_payment",
            description_override="Track and process payment confirmations including UTR numbers, cheque details, and payment receipts.",
        )
        async def track_payment(
            sender_email: str,
            payment_type: str,  # "utr", "cheque", "cash", "online"
            payment_reference: str,
            amount: Optional[float] = None,
            order_id: Optional[str] = None,
        ) -> str:
            """Track payment information"""
            import json
            import re

            try:
                # Validate UTR if payment type is UTR
                if payment_type == "utr":
                    # UTR validation pattern (12-22 digits)
                    utr_pattern = r"^\d{12,22}$"
                    if not re.match(utr_pattern, payment_reference):
                        logger.warning(f"Invalid UTR format: {payment_reference}")
                        return json.dumps(
                            {
                                "success": False,
                                "error": "Invalid UTR format",
                                "payment_reference": payment_reference,
                                "expected_format": "12-22 digit number",
                            }
                        )

                # TODO: Save payment to database
                # For now, create mock payment record
                payment_record = {
                    "payment_id": f"PAY_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "customer_email": sender_email,
                    "payment_type": payment_type,
                    "payment_reference": payment_reference,
                    "amount": amount,
                    "order_id": order_id,
                    "status": "verified",
                    "recorded_at": datetime.now().isoformat(),
                    "requires_manual_verification": payment_type == "cheque",
                }

                logger.info(
                    f"Payment tracked: {payment_type} - {payment_reference} from {sender_email}"
                )

                # Determine next actions
                next_actions = []
                if order_id:
                    next_actions.append("update_order_status to 'payment_received'")
                    next_actions.append("send_email_response with payment confirmation")
                else:
                    next_actions.append("match_payment_to_order using customer email")
                    next_actions.append("send_email_response requesting order details")

                result = {
                    "success": True,
                    "payment_tracked": True,
                    "payment_record": payment_record,
                    "confidence": 0.95 if payment_type == "utr" else 0.8,
                    "next_actions": next_actions,
                    "requires_human_review": payment_type == "cheque"
                    or amount > 100000,
                }

                return json.dumps(result)

            except Exception as e:
                logger.error(f"Error tracking payment: {e}")
                return json.dumps(
                    {
                        "success": False,
                        "error": str(e),
                        "payment_reference": payment_reference,
                        "requires_human_review": True,
                    }
                )

        tools.append(track_payment)

        # Handle supplier inquiry tool
        @function_tool(
            name_override="handle_supplier_inquiry",
            description_override="Handle supplier communications, vendor inquiries, and procurement-related emails.",
        )
        async def handle_supplier_inquiry(
            supplier_email: str, inquiry_type: str, email_subject: str, email_body: str
        ) -> str:
            """Handle supplier communications"""
            import json

            try:
                # Analyze supplier inquiry
                inquiry_types = {
                    "quotation": "Price quotation request",
                    "material_availability": "Raw material availability check",
                    "delivery_schedule": "Delivery timeline inquiry",
                    "payment_terms": "Payment terms discussion",
                    "quality_concern": "Quality issue report",
                    "new_vendor": "New vendor registration",
                }

                # Create inquiry record
                inquiry_record = {
                    "inquiry_id": f"INQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "supplier_email": supplier_email,
                    "inquiry_type": inquiry_type,
                    "description": inquiry_types.get(inquiry_type, "General inquiry"),
                    "subject": email_subject,
                    "priority": (
                        "high"
                        if inquiry_type in ["quality_concern", "delivery_schedule"]
                        else "medium"
                    ),
                    "received_at": datetime.now().isoformat(),
                }

                # Determine routing
                routing = {
                    "quotation": "procurement_team",
                    "material_availability": "inventory_team",
                    "delivery_schedule": "production_planning",
                    "payment_terms": "finance_team",
                    "quality_concern": "quality_assurance",
                    "new_vendor": "vendor_management",
                }

                route_to = routing.get(inquiry_type, "procurement_team")

                result = {
                    "success": True,
                    "inquiry_processed": True,
                    "inquiry_record": inquiry_record,
                    "routed_to": route_to,
                    "auto_response_sent": True,
                    "response_message": f"Your {inquiry_types.get(inquiry_type, 'inquiry')} has been received and forwarded to our {route_to.replace('_', ' ')}. We will respond within 24 hours.",
                    "requires_human_review": inquiry_type
                    in ["quality_concern", "new_vendor"],
                    "confidence": 0.85,
                }

                logger.info(
                    f"Supplier inquiry processed: {inquiry_type} from {supplier_email}, routed to {route_to}"
                )

                return json.dumps(result)

            except Exception as e:
                logger.error(f"Error handling supplier inquiry: {e}")
                return json.dumps(
                    {
                        "success": False,
                        "error": str(e),
                        "supplier_email": supplier_email,
                        "requires_human_review": True,
                    }
                )

        tools.append(handle_supplier_inquiry)

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
                self._current_attachments = attachments_data
                logger.info(f"Stored {len(attachments_data)} attachments in context")

                # Construct prompt for autonomous processing with classification
                # Don't truncate the email body - it's crucial for extraction
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

                # Include the last order result if available
                result_dict = {
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

                # Add the actual order processing result if available
                if hasattr(self, "_last_order_result") and self._last_order_result:
                    result_dict["order_result"] = self._last_order_result
                    # Pass the actual list if available, otherwise the count
                    if "image_matches_list" in self._last_order_result:
                        result_dict["image_matches"] = self._last_order_result[
                            "image_matches_list"
                        ]
                    else:
                        result_dict["image_matches"] = self._last_order_result.get(
                            "image_matches", 0
                        )
                    result_dict["items"] = self._last_order_result.get("items", [])

                return result_dict

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

    def _get_tools_for_intent(self, intent: str) -> List[str]:
        """Get recommended tools based on intent"""
        tool_mapping = {
            "NEW_ORDER": [
                "process_complete_order",
                "generate_document",
                "send_email_response",
            ],
            "ORDER_MODIFICATION": [
                "get_order_status",
                "update_order",
                "send_email_response",
            ],
            "URGENT_ORDER": [
                "process_complete_order",
                "priority_flag",
                "send_email_response",
            ],
            "PAYMENT": ["track_payment", "update_order_status", "send_email_response"],
            "PAYMENT_INQUIRY": ["check_payment_status", "send_email_response"],
            "INQUIRY": [
                "search_inventory",
                "get_customer_context",
                "send_email_response",
            ],
            "QUOTATION_REQUEST": [
                "calculate_quote",
                "generate_document",
                "send_email_response",
            ],
            "NEW_CUSTOMER": [
                "create_customer",
                "send_welcome_package",
                "send_email_response",
            ],
            "FOLLOWUP": ["get_order_status", "send_email_response"],
            "SUPPLIER": [
                "handle_supplier_inquiry",
                "forward_to_procurement",
                "send_email_response",
            ],
            "MATERIAL_QUOTATION": [
                "process_supplier_quote",
                "compare_prices",
                "send_email_response",
            ],
            "DELIVERY_UPDATE": [
                "update_delivery_status",
                "notify_customer",
                "send_email_response",
            ],
            "COMPLAINT": [
                "create_ticket",
                "get_customer_context",
                "send_email_response",
            ],
            "QUALITY_ISSUE": [
                "create_quality_report",
                "notify_qa_team",
                "send_email_response",
            ],
            "INVOICE_REQUEST": ["generate_invoice", "send_email_response"],
        }
        return tool_mapping.get(intent, ["get_customer_context", "send_email_response"])

    async def _update_sender_pattern(
        self,
        sender_email: str,
        recipient_email: str,
        recipient_description: str,
        intent: str,
        subject: str,
    ):
        """Update pattern with business context"""
        try:
            from ..factory_database.connection import get_db
            from ..factory_database.models import EmailPattern

            with get_db() as db:
                pattern = (
                    db.query(EmailPattern)
                    .filter_by(
                        sender_email=sender_email,
                        recipient_email=recipient_email,
                        intent_type=intent,
                    )
                    .first()
                )

                if pattern:
                    pattern.count += 1
                    pattern.last_seen = datetime.utcnow()
                    pattern.recipient_description = (
                        recipient_description  # Update description
                    )

                    # Update subject keywords
                    if pattern.subject_keywords:
                        keywords = json.loads(pattern.subject_keywords)
                    else:
                        keywords = []
                    keywords.extend(subject.lower().split()[:5])
                    pattern.subject_keywords = json.dumps(list(set(keywords))[:20])
                else:
                    pattern = EmailPattern(
                        sender_email=sender_email,
                        recipient_email=recipient_email,
                        recipient_description=recipient_description,
                        intent_type=intent,
                        count=1,
                        subject_keywords=json.dumps(subject.lower().split()[:5]),
                    )
                    db.add(pattern)

                db.commit()
                logger.info(
                    f"Pattern updated: {sender_email}→{recipient_email} ({intent})"
                )
        except Exception as e:
            logger.error(f"Failed to update pattern: {e}")

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
