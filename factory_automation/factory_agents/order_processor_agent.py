"""Advanced Order Processor Agent with full workflow integration"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
from openai import AsyncOpenAI

from ..factory_config.settings import settings
from ..factory_database.connection import get_db
from ..factory_database.models import Customer, Order
from ..factory_database.models import OrderItem as DBOrderItem
from ..factory_database.vector_db import ChromaDBClient
from ..factory_models.ai_extraction_models import (
    AIExtractedOrder,
)
from ..factory_models.ai_extraction_models import CustomerInformation as AICustomerInfo
from ..factory_models.ai_extraction_models import (
    OrderItemAI,
)
from ..factory_models.order_models import (
    Attachment,
    AttachmentType,
    CustomerInfo,
    DeliveryInfo,
    ExtractedOrder,
    FitTagMapping,
    HumanReviewResponse,
    InventoryUpdate,
    Material,
    OrderConfirmation,
    OrderItem,
    OrderPriority,
    OrderProcessingResult,
    ProformaInvoice,
    TagSpecification,
    TagType,
)
from ..factory_rag.enhanced_search import EnhancedRAGSearch
from .human_interaction_manager import HumanInteractionManager
from .image_processor_agent import ImageProcessorAgent
from .visual_similarity_search import VisualSimilaritySearch

logger = logging.getLogger(__name__)


class OrderProcessorAgent:
    """Complete order processing with AI extraction, ChromaDB search, and human review"""

    def __init__(
        self,
        chromadb_client: ChromaDBClient,
        human_manager: Optional[HumanInteractionManager] = None,
    ):
        """Initialize order processor"""
        self.chromadb_client = chromadb_client
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.image_processor = ImageProcessorAgent(chromadb_client)
        self.human_manager = human_manager or HumanInteractionManager()
        self.visual_search = VisualSimilaritySearch(
            chromadb_client
        )  # Visual similarity search

        # Lazy-load enhanced search to avoid startup timeout
        self._enhanced_search = None

    @property
    def enhanced_search(self):
        """Lazy-load enhanced search when first accessed"""
        if self._enhanced_search is None:
            logger.info("Initializing enhanced search on first use...")
            self._enhanced_search = EnhancedRAGSearch(
                chromadb_client=self.chromadb_client,
                enable_reranking=True,
                enable_hybrid_search=True,
            )
        return self._enhanced_search

    async def process_order_email(
        self,
        email_subject: str,
        email_body: str,
        email_date: datetime,
        sender_email: str,
        attachments: List[Dict[str, Any]] = None,
    ) -> OrderProcessingResult:
        """Process complete order from email with attachments"""

        start_time = datetime.now()

        try:
            # Step 1: Extract order data using AI
            extracted_order = await self._extract_order_with_ai(
                email_subject, email_body, email_date, sender_email, attachments
            )

            # Step 2: Process attachments
            if attachments:
                await self._process_attachments(extracted_order, attachments)
                # Recalculate confidence after processing attachments
                extracted_order.extraction_confidence = (
                    self._recalculate_confidence_with_attachments(extracted_order)
                )

            # Step 3: Search inventory for each item
            inventory_matches = await self._search_inventory_for_items(extracted_order)

            # Step 4: Calculate confidence scores
            confidence_scores = self._calculate_confidence_scores(
                extracted_order, inventory_matches
            )

            # Step 5: Determine action based on confidence
            recommended_action = self._determine_action(
                extracted_order.extraction_confidence, confidence_scores
            )

            # Step 6: Handle based on recommended action
            if recommended_action == "auto_approve":
                inventory_updates = await self._auto_approve_order(extracted_order)
            elif recommended_action == "human_review":
                await self._request_human_review(extracted_order, inventory_matches)
                inventory_updates = []
            else:  # request_clarification
                await self._request_clarification(extracted_order)
                inventory_updates = []

            # Calculate processing time
            processing_time_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )

            # Separate image matches from text matches
            image_matches = [m for m in inventory_matches if m.get("type") == "image"]
            text_matches = [m for m in inventory_matches if m.get("type") != "image"]

            return OrderProcessingResult(
                order=extracted_order,
                inventory_matches=text_matches,  # Text-based matches
                image_matches=image_matches,  # Image-based matches
                confidence_scores=confidence_scores,
                recommended_action=recommended_action,
                inventory_updates=inventory_updates,
                processing_time_ms=processing_time_ms,
                errors=[],
                warnings=[],
            )

        except Exception as e:
            logger.error(f"Error processing order: {e}")
            processing_time_ms = int(
                (datetime.now() - start_time).total_seconds() * 1000
            )

            return OrderProcessingResult(
                order=extracted_order if "extracted_order" in locals() else None,
                inventory_matches=[],
                confidence_scores={},
                recommended_action="request_clarification",
                inventory_updates=[],
                processing_time_ms=processing_time_ms,
                errors=[str(e)],
                warnings=[],
            )

    async def _extract_order_with_ai(
        self,
        email_subject: str,
        email_body: str,
        email_date: datetime,
        sender_email: str,
        attachments: List[Dict[str, Any]] = None,
    ) -> ExtractedOrder:
        """Extract order data using GPT-4"""

        # Prepare extraction prompt
        extraction_prompt = f"""
        Analyze this order email from a garment tag manufacturing context and extract comprehensive order details.
        
        Email Subject: {email_subject}
        Sender: {sender_email}
        Date: {email_date}
        
        Email Body:
        {email_body}
        
        Attachments mentioned: {len(attachments) if attachments else 0}
        
        Extract and structure the following:
        1. Customer information (company, contact person, email, phone)
        2. Order items with specifications:
           - Tag codes (e.g., TBALWBL0009N)
           - Tag types (fit tags, main tags, price tags, care labels, etc.)
           - Quantities (look for any numbers followed by units like pcs, pieces, tags, units)
           - Remarks/special requirements
           - Fit mappings if mentioned
        3. Proforma invoice details if mentioned
        4. Delivery requirements and urgency
        5. Any brand information (Allen Solly, Peter England, Van Heusen, Myntra, etc.)
        
        IMPORTANT: 
        - This is an order email to a garment tag manufacturer, so there MUST be items being ordered
        - If specific tag codes aren't mentioned, infer from context (e.g., "price tags" = generic price tag order)
        - If quantities aren't clear, look for any numbers that could represent quantities
        - Common tag types: price tags, care labels, size tags, brand tags, wash care labels, fit tags
        - If brand is mentioned anywhere, associate it with the items
        - Extract AT LEAST one item even if details are vague
        
        Pay special attention to:
        - Any mention of tags, labels, stickers, hangtags
        - Brand names (Allen Solly, Peter England, Van Heusen, etc.)
        - Numbers that could be quantities
        - Product codes and SKUs
        - Delivery dates
        
        Return as structured JSON matching the ExtractedOrder schema.
        """

        try:
            # Check if beta parse method is available (requires OpenAI SDK 1.50+)
            if hasattr(self.openai_client, "beta") and hasattr(
                self.openai_client.beta, "chat"
            ):
                try:
                    # Use the new structured output API (requires gpt-4o or gpt-4o-mini)
                    response = await self.openai_client.beta.chat.completions.parse(
                        model="gpt-4o-mini",  # Changed from gpt-4-turbo-preview
                        messages=[
                            {
                                "role": "system",
                                "content": """You are an expert at extracting structured order information from garment industry emails.
                                This is a garment tag manufacturing company, so ALL emails are about ordering tags/labels.
                                Focus on finding: tag types, quantities, brands, and special requirements.
                                ALWAYS extract at least one item being ordered, even if you have to infer from context.
                                Common items ordered: price tags, care labels, size tags, brand labels, wash care labels.
                                If no specific items are mentioned, assume they want price tags.""",
                            },
                            {"role": "user", "content": extraction_prompt},
                        ],
                        response_format=AIExtractedOrder,  # Direct Pydantic model
                        temperature=0.1,
                        max_tokens=3000,
                    )

                    # Access the parsed Pydantic model directly
                    ai_order = response.choices[0].message.parsed

                    # If parsing failed, AI returns None
                    if ai_order is None:
                        raise ValueError("AI returned None for structured output")

                except Exception as e:
                    logger.warning(
                        f"Structured output API failed: {e}. Falling back to JSON mode..."
                    )
                    # Fall back to JSON mode
                    response = await self.openai_client.chat.completions.create(
                        model="gpt-4-turbo-preview",  # Can use turbo for JSON mode
                        messages=[
                            {
                                "role": "system",
                                "content": """You are an expert at extracting structured order information from garment industry emails.
                                Return a JSON object with: customer_information, order_items, delivery_requirements.
                                ALWAYS include at least one item in order_items.""",
                            },
                            {"role": "user", "content": extraction_prompt},
                        ],
                        response_format={"type": "json_object"},
                        temperature=0.1,
                        max_tokens=3000,
                    )

                    # Parse JSON manually
                    raw_data = json.loads(response.choices[0].message.content)

                    # Get order items or create default
                    items = raw_data.get("order_items", raw_data.get("items", []))
                    if not items:
                        items = [
                            OrderItemAI(
                                tag_code="GENERIC", tag_type="price_tag", quantity=1
                            )
                        ]

                    # Create AI order with defaults for required fields
                    ai_order = AIExtractedOrder(
                        customer_information=AICustomerInfo(
                            company=raw_data.get("customer_information", {}).get(
                                "company", "Unknown"
                            ),
                            email=raw_data.get("customer_information", {}).get(
                                "email", sender_email
                            ),
                        ),
                        order_items=items,
                        delivery_requirements=raw_data.get("delivery_requirements"),
                        brand=raw_data.get("brand"),
                        po_number=raw_data.get("po_number"),
                        special_instructions=raw_data.get("special_instructions"),
                    )
            else:
                # Old SDK version - use JSON mode
                logger.info(
                    "Using JSON mode (OpenAI SDK doesn't support structured outputs)"
                )
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=[
                        {
                            "role": "system",
                            "content": """You are an expert at extracting structured order information.
                            Return JSON with: customer_information, order_items, delivery_requirements.""",
                        },
                        {"role": "user", "content": extraction_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.1,
                    max_tokens=3000,
                )

                raw_data = json.loads(response.choices[0].message.content)

                # Get order items or create default
                items = raw_data.get("order_items", raw_data.get("items", []))
                if not items:
                    items = [
                        OrderItemAI(
                            tag_code="GENERIC", tag_type="price_tag", quantity=1
                        )
                    ]

                ai_order = AIExtractedOrder(
                    customer_information=AICustomerInfo(
                        company=raw_data.get("customer_information", {}).get(
                            "company", "Unknown"
                        ),
                        email=raw_data.get("customer_information", {}).get(
                            "email", sender_email
                        ),
                    ),
                    order_items=items,
                )

            # Log what the AI extracted (convert model to dict for logging)
            if ai_order:
                logger.info(
                    f"AI extracted data: {ai_order.model_dump_json(indent=2)[:500]}..."
                )
            else:
                logger.warning("AI returned None for order extraction")
                # Create empty model as fallback
                ai_order = AIExtractedOrder()

            # Get items using helper method
            items_data = ai_order.get_order_items()
            logger.info(f"Number of items extracted: {len(items_data)}")

            # If no items extracted, create a default item based on email content
            if not items_data:
                logger.warning(
                    "AI didn't extract any items. Creating default order item..."
                )
                # Try to find any quantity mentioned
                import re

                qty_match = re.search(
                    r"(\d+)\s*(pcs|pieces|tags|units|nos)?", email_body, re.IGNORECASE
                )
                quantity = (
                    int(qty_match.group(1)) if qty_match else 100
                )  # Default to 100

                # Try to find brand
                brand_patterns = [
                    "Allen Solly",
                    "Peter England",
                    "Van Heusen",
                    "Louis Philippe",
                    "Myntra",
                ]
                brand_found = "Unknown"
                for brand in brand_patterns:
                    if brand.lower() in email_body.lower():
                        brand_found = brand
                        break

                # Create a default item - use same field name as AI returns
                # Create a default item using our AI model
                default_item = OrderItemAI(
                    tag_code="GENERIC-PRICE-TAG",
                    tag_type="price_tag",
                    quantity=quantity,
                    brand=brand_found,
                    remarks="Extracted from email context - needs verification",
                )
                items_data = [default_item]
                logger.info(
                    f"Created default item: {quantity} price tags for {brand_found}"
                )

            # Convert AI items to our strict OrderItem model
            order_items = []
            for item_data in items_data:
                # Handle both dict and Pydantic model
                if isinstance(item_data, OrderItemAI):
                    item_dict = item_data.model_dump()
                else:
                    item_dict = item_data
                # Normalize tag type (convert "Fit Tag" to "fit_tag", etc.)
                tag_type_raw = item_dict.get("tag_type", "other")
                tag_type_normalized = (
                    tag_type_raw.lower().replace(" ", "_").replace("-", "_")
                )

                # Map common variations to valid enum values
                tag_type_mapping = {
                    "fit_tag": TagType.FIT_TAG,
                    "price_tag": TagType.PRICE_TAG,
                    "price_tags": TagType.PRICE_TAG,
                    "hang_tag": TagType.HANG_TAG,
                    "care_label": TagType.CARE_LABEL,
                    "care_labels": TagType.CARE_LABEL,
                    "brand_label": TagType.BRAND_LABEL,
                    "size_label": TagType.SIZE_LABEL,
                    "main_tag": TagType.MAIN_TAG,
                    "barcode_sticker": TagType.BARCODE_STICKER,
                    "woven_label": TagType.WOVEN_LABEL,
                    "printed_label": TagType.PRINTED_LABEL,
                    "sustainability_tag": TagType.SUSTAINABILITY_TAG,
                }

                tag_type_enum = tag_type_mapping.get(tag_type_normalized, TagType.OTHER)

                # Handle both single tag_code and multiple tag_codes
                tag_codes = item_dict.get("tag_codes", [])
                tag_code = item_dict.get("tag_code")

                # If we have multiple tag codes, create an item for each
                if tag_codes and isinstance(tag_codes, list):
                    # Use the first code as primary, or combine them
                    tag_code = tag_codes[0] if tag_codes else "UNKNOWN"
                    # Could also join them: tag_code = ", ".join(tag_codes)
                elif not tag_code:
                    tag_code = "UNKNOWN"

                # Get quantity and ensure it's positive
                quantity = item_dict.get("quantity", 1)
                if quantity is None:
                    quantity = 1
                elif isinstance(quantity, str):
                    # Try to extract number from string
                    import re

                    qty_match = re.search(r"\d+", str(quantity))
                    quantity = int(qty_match.group()) if qty_match else 1
                elif quantity <= 0:
                    quantity = 1  # Default to 1 if 0 or negative

                # Create TagSpecification
                tag_spec = TagSpecification(
                    tag_code=tag_code,
                    tag_type=tag_type_enum,
                    quantity=quantity,
                    color=item_dict.get("color"),
                    size=item_dict.get("size"),
                    material=(
                        Material(item_dict.get("material", "other"))
                        if item_dict.get("material")
                        else None
                    ),
                    remarks=item_dict.get("remarks"),
                )

                # Create FitTagMapping if fit information is present
                fit_mapping = None
                if item_dict.get("fit"):
                    # Create basic mapping from fit field
                    fit_mapping = FitTagMapping(
                        fit_type=item_dict.get("fit", "Unknown"),
                        fit_tag_codes=tag_codes if tag_codes else [tag_code],
                        main_tag_code=tag_code,
                        main_tag_remark=item_dict.get("remarks"),
                    )

                # Create OrderItem - ensure brand is never None
                item_brand = item_dict.get("brand")
                if not item_brand:  # Handle None, empty string, etc.
                    item_brand = ai_order.get_brand() or "Unknown"

                order_item = OrderItem(
                    item_id=f"ITEM-{len(order_items)+1:03d}",
                    tag_specification=tag_spec,
                    brand=item_brand,
                    category=item_dict.get("category"),
                    fit_mapping=fit_mapping,
                    quantity_ordered=quantity,
                )

                order_items.append(order_item)

            # Get customer info using helper method
            customer_info = ai_order.get_customer_info()

            # Create customer info
            customer = CustomerInfo(
                company_name=customer_info.company
                or customer_info.contact_person
                or "Unknown",
                contact_person=customer_info.contact_person,
                email=customer_info.email or sender_email,
                phone=customer_info.phone,
            )

            # Get delivery info using helper method
            delivery_info = ai_order.get_delivery_info()

            # Map urgency strings to enum
            urgency_str = (delivery_info.urgency or "normal").lower()
            urgency_map = {
                "urgent": OrderPriority.URGENT,
                "high": OrderPriority.HIGH,
                "medium": OrderPriority.MEDIUM,
                "low": OrderPriority.LOW,
                "normal": OrderPriority.NORMAL,
            }
            urgency = urgency_map.get(urgency_str, OrderPriority.NORMAL)

            # Create delivery info
            delivery = DeliveryInfo(
                required_date=(
                    datetime.fromisoformat(delivery_info.delivery_date)
                    if delivery_info.delivery_date
                    else None
                ),
                urgency=urgency,
                special_instructions=delivery_info.special_instructions
                or ai_order.special_instructions,
            )

            # Create proforma invoice if present
            proforma = None
            if ai_order.proforma_invoice_details:
                invoice_data = ai_order.proforma_invoice_details
                proforma = ProformaInvoice(
                    invoice_number=invoice_data.invoice_number or "Unknown",
                    invoice_date=(
                        datetime.fromisoformat(invoice_data.invoice_date)
                        if invoice_data.invoice_date
                        else None
                    ),
                )

            # Calculate extraction confidence
            # Convert model to dict for confidence calculation
            raw_data = ai_order.model_dump() if ai_order else {}
            confidence = self._calculate_extraction_confidence(raw_data)

            # Log order items before creating ExtractedOrder
            logger.info(f"Created {len(order_items)} order items from extraction")
            if order_items:
                logger.info(
                    f"First item: {order_items[0].tag_specification.tag_code if order_items else 'None'}"
                )

            # Ensure we always have at least one item
            if not order_items:
                logger.warning(
                    "No order items created. Adding generic item for search..."
                )
                # Create a generic item to ensure search happens
                generic_item = OrderItem(
                    item_id="ITEM-001",
                    tag_specification=TagSpecification(
                        tag_code="GENERIC-TAG",
                        tag_type=TagType.price_tag,
                        quantity=100,
                        remarks="Generic order - needs clarification",
                    ),
                    brand=ai_order.get_brand() or "Unknown",
                    quantity_ordered=100,
                )
                order_items.append(generic_item)

            # Create ExtractedOrder
            extracted_order = ExtractedOrder(
                email_subject=email_subject,
                email_date=email_date,
                customer=customer,
                items=order_items,
                proforma_invoice=proforma,
                purchase_order_number=ai_order.po_number
                or ai_order.purchase_order_number,
                delivery=delivery,
                extraction_confidence=(
                    confidence if order_items else 0.2
                ),  # Low confidence if we had to add generic
                extraction_method="ai_gpt4",
                missing_information=ai_order.missing_information or [],
                requires_clarification=len(order_items) == 0 or confidence < 0.6,
            )

            return extracted_order

        except Exception as e:
            logger.error(f"AI extraction failed: {e}")
            # Return minimal order with low confidence
            return ExtractedOrder(
                email_subject=email_subject,
                email_date=email_date,
                customer=CustomerInfo(company_name="Unknown", email=sender_email),
                items=[],
                delivery=DeliveryInfo(),
                extraction_confidence=0.0,
                extraction_method="failed",
                requires_clarification=True,
                missing_information=["Failed to extract order details"],
            )

    async def _process_attachments(
        self, order: ExtractedOrder, attachments: List[Dict[str, Any]]
    ):
        """Process email attachments (Excel, images, PDFs)"""

        for att in attachments:
            filename = att.get("filename", "")
            filepath = att.get("filepath", "")  # Get file path instead of content

            # Skip if no filepath provided
            if not filepath:
                logger.warning(f"No filepath provided for attachment: {filename}")
                # Add empty attachment record
                order.attachments.append(
                    Attachment(
                        filename=filename,
                        type=AttachmentType.OTHER,
                        mime_type=att.get("mime_type"),
                        extracted_data={"error": "No filepath provided"},
                    )
                )
                continue

            # Determine attachment type and process
            if filename.endswith((".xlsx", ".xls", ".csv")):
                att_type = AttachmentType.EXCEL  # Treat CSV as Excel type
                # Process Excel/CSV file
                extracted_data = await self._process_excel_attachment(
                    filepath, filename
                )

                # Check if Excel had embedded images that were extracted
                if (
                    hasattr(self, "_excel_extracted_images")
                    and self._excel_extracted_images
                ):
                    logger.info(
                        f"Processing {len(self._excel_extracted_images)} images extracted from Excel"
                    )
                    for img_info in self._excel_extracted_images:
                        # Process each extracted image
                        img_result = await self._process_image_attachment(
                            img_info["filepath"],
                            img_info["filename"],
                            order.order_id,
                            order.customer.company_name,
                        )
                        # Add as separate attachment
                        order.attachments.append(
                            Attachment(
                                filename=img_info["filename"],
                                type=AttachmentType.IMAGE,
                                mime_type=img_info["mime_type"],
                                file_path=img_info["filepath"],
                                extracted_data=img_result,
                            )
                        )
                    # Clear the temporary storage
                    self._excel_extracted_images = []
            elif filename.endswith((".jpg", ".jpeg", ".png", ".gif")):
                att_type = AttachmentType.IMAGE
                # Process image with Qwen2.5VL
                extracted_data = await self._process_image_attachment(
                    filepath, filename, order.order_id, order.customer.company_name
                )
            elif filename.endswith(".pdf"):
                att_type = AttachmentType.PDF
                extracted_data = await self._process_pdf_attachment(filepath, filename)
            elif filename.endswith((".doc", ".docx")):
                att_type = AttachmentType.WORD
                extracted_data = await self._process_word_attachment(filepath, filename)
            else:
                att_type = AttachmentType.OTHER
                extracted_data = None

            # Add to order attachments
            order.attachments.append(
                Attachment(
                    filename=filename,
                    type=att_type,
                    mime_type=att.get("mime_type"),
                    extracted_data=extracted_data,
                )
            )

    async def _process_image_attachment(
        self, filepath: str, filename: str, order_id: str, customer_name: str
    ) -> Dict[str, Any]:
        """Process image attachment using Qwen2.5VL and store in ChromaDB"""

        try:
            # Check if filepath is valid
            if not filepath:
                logger.error(f"Empty filepath for image attachment: {filename}")
                return {"error": "Empty filepath", "filename": filename}

            # Directly use the file path
            if not os.path.exists(filepath):
                logger.error(
                    f"Image attachment file not found: {filepath} (filename: {filename})"
                )
                raise FileNotFoundError(f"Attachment file not found: {filepath}")

            # Process and store in ChromaDB
            result = await self.image_processor.process_and_store_image(
                image_path=filepath,
                order_id=order_id,
                customer_name=customer_name,
                additional_metadata={
                    "original_filename": filename,
                    "source": "email_attachment",
                },
            )

            return result

        except Exception as e:
            logger.error(f"Error processing image attachment: {e}")
            return {"error": str(e)}

    async def _process_excel_attachment(
        self, filepath: str, filename: str
    ) -> Dict[str, Any]:
        """Process Excel attachment to extract order data and embedded images"""

        try:
            # Check if filepath is valid
            if not filepath:
                logger.error(f"Empty filepath for Excel attachment: {filename}")
                return {"error": "Empty filepath", "filename": filename}

            # Directly use the file path
            if not os.path.exists(filepath):
                logger.error(
                    f"Excel attachment file not found: {filepath} (filename: {filename})"
                )
                raise FileNotFoundError(f"Attachment file not found: {filepath}")

            # Use enhanced Excel processor to extract data AND images
            from .excel_with_images_processor import process_excel_with_images

            result = await process_excel_with_images(filepath, filename)

            if result.get("error"):
                logger.error(f"Error processing Excel: {result['error']}")
                return {"error": result["error"], "filename": filename}

            # Process extracted images if any
            extracted_images = result.get("images", [])
            if extracted_images:
                logger.info(f"Found {len(extracted_images)} embedded images in Excel")
                # Store image paths for later processing
                self._excel_extracted_images = extracted_images

            # Get the data
            excel_data = result.get("data", [])
            if excel_data:
                df = pd.DataFrame(excel_data)
            else:
                df = pd.DataFrame()

            # Extract relevant data
            extracted_data = {
                "filename": filename,
                "rows": len(df),
                "columns": list(df.columns) if not df.empty else [],
                "data": df.to_dict(orient="records") if not df.empty else [],
            }

            # Add image info if images were extracted
            if extracted_images:
                extracted_data["embedded_images"] = len(extracted_images)
                extracted_data["image_files"] = [
                    img["filename"] for img in extracted_images
                ]

            return extracted_data

        except Exception as e:
            logger.error(f"Error processing Excel attachment: {e}")
            return {"error": str(e)}

    async def _process_pdf_attachment(
        self, filepath: str, filename: str
    ) -> Dict[str, Any]:
        """Process PDF attachment using pdfplumber with error handling"""
        try:
            import pdfplumber
        except ImportError:
            logger.error("pdfplumber not installed")
            return {
                "error": "PDF processing library not available",
                "filename": filename,
            }

        try:
            # Check if filepath is valid
            if not filepath:
                logger.error(f"Empty filepath for PDF attachment: {filename}")
                return {"error": "Empty filepath", "filename": filename}

            # Directly use the file path
            if not os.path.exists(filepath):
                logger.error(
                    f"PDF attachment file not found: {filepath} (filename: {filename})"
                )
                return {"error": f"File not found: {filepath}", "filename": filename}

            # Extract text and tables from PDF with safety limits
            extracted_text = []
            extracted_tables = []
            max_pages = 10  # Limit pages to prevent memory issues
            max_text_length = 50000  # Limit total text length

            with pdfplumber.open(filepath) as pdf:
                logger.info(f"Processing PDF {filename} with {len(pdf.pages)} pages")

                # Process limited number of pages
                pages_to_process = min(len(pdf.pages), max_pages)
                total_text_length = 0

                for page_num, page in enumerate(pdf.pages[:pages_to_process]):
                    try:
                        # Extract text with length limit
                        text = page.extract_text()
                        if text:
                            # Check if we've exceeded text limit
                            if total_text_length + len(text) > max_text_length:
                                logger.warning(
                                    f"PDF {filename}: Text limit reached at page {page_num+1}"
                                )
                                break
                            extracted_text.append(f"Page {page_num + 1}:\n{text}")
                            total_text_length += len(text)

                        # Extract tables (limit to first 5 tables total)
                        if len(extracted_tables) < 5:
                            tables = page.extract_tables()
                            for table in tables:
                                if table and len(extracted_tables) < 5:
                                    extracted_tables.append(
                                        {"page": page_num + 1, "data": table}
                                    )
                    except Exception as e:
                        logger.warning(
                            f"Error processing page {page_num+1} of {filename}: {e}"
                        )
                        continue

                if len(pdf.pages) > max_pages:
                    logger.info(
                        f"PDF {filename}: Processed first {max_pages} of {len(pdf.pages)} pages"
                    )

            return {
                "filename": filename,
                "type": "pdf",
                "pages": len(pdf.pages) if "pdf" in locals() else 0,
                "text": "\n\n".join(extracted_text),
                "tables": extracted_tables,
                "status": "processed",
            }

        except Exception as e:
            logger.error(f"Error processing PDF attachment: {e}")
            return {"filename": filename, "type": "pdf", "error": str(e)}

    async def _process_word_attachment(
        self, filepath: str, filename: str
    ) -> Dict[str, Any]:
        """Process Word document attachment"""
        try:
            # Check if filepath is valid
            if not filepath:
                logger.error(f"Empty filepath for Word attachment: {filename}")
                return {"error": "Empty filepath", "filename": filename}

            # Directly use the file path
            if not os.path.exists(filepath):
                logger.error(
                    f"Word attachment file not found: {filepath} (filename: {filename})"
                )
                raise FileNotFoundError(f"Attachment file not found: {filepath}")

            # TODO: Implement Word document processing (requires python-docx library)
            # For now, just acknowledge the file exists
            return {
                "filename": filename,
                "type": "word",
                "filepath": filepath,
                "status": "file_exists_not_processed",
            }
        except Exception as e:
            logger.error(f"Error processing Word attachment: {e}")
            return {"filename": filename, "type": "word", "error": str(e)}

    async def _search_inventory_for_items(
        self, order: ExtractedOrder
    ) -> List[Dict[str, Any]]:
        """Search inventory using enhanced search with reranking"""

        all_matches = []

        # Log what we're searching for
        logger.info(f"Searching inventory for {len(order.items)} items")
        if not order.items:
            logger.warning("No items to search for in order!")
            return []

        for item in order.items:
            # Create search query from item details
            # Build query parts, filtering out generic/unknown values
            query_parts = []

            # Add brand if it's not generic
            if item.brand and item.brand not in ["Unknown", "GENERIC"]:
                query_parts.append(item.brand)

            # Add tag code if it's not generic
            if (
                item.tag_specification.tag_code
                and "GENERIC" not in item.tag_specification.tag_code
            ):
                query_parts.append(item.tag_specification.tag_code)

            # Always add tag type
            tag_type_str = item.tag_specification.tag_type.value.replace("_", " ")
            query_parts.append(tag_type_str)

            # Add specific attributes
            if item.tag_specification.color:
                query_parts.append(item.tag_specification.color)
            if item.tag_specification.material:
                query_parts.append(item.tag_specification.material)

            # Build search query
            search_query = " ".join(query_parts) if query_parts else "price tag"

            # If query is too generic, try to make it more specific
            if search_query in ["price tag", "tag", "label"]:
                # Try to add brand context from the order
                if item.brand and item.brand != "Unknown":
                    search_query = f"{item.brand} {search_query}"
                else:
                    # Search for common tag types
                    search_query = "garment price tag label"

            # Log the search query
            logger.info(f"Searching for item {item.item_id}: '{search_query}'")

            # Prepare filters - only use brand filter if it's specific
            filters = None
            if item.brand and item.brand not in ["Unknown", "GENERIC"]:
                filters = {"brand": item.brand}
                logger.debug(f"Using brand filter: {item.brand}")

            # Use enhanced search with reranking
            try:
                search_results, search_stats = self.enhanced_search.search(
                    query=search_query,
                    n_results=10,  # Get more results
                    n_candidates=30,  # Get more candidates for reranking
                    filters=filters,
                )
            except Exception as e:
                logger.error(f"Search failed for query '{search_query}': {e}")
                search_results = []
                search_stats = {"final_results": 0, "semantic_candidates": 0}

            # Log search results
            logger.info(f"Found {len(search_results)} results for item {item.item_id}")

            # If no results, try a broader search
            if not search_results and search_query != "tag":
                logger.info(
                    f"No results for '{search_query}'. Trying broader search..."
                )
                try:
                    # Try with just "tag" or "label"
                    broader_query = "tag" if "tag" in search_query.lower() else "label"
                    search_results, search_stats = self.enhanced_search.search(
                        query=broader_query,
                        n_results=5,
                        n_candidates=20,
                        filters=None,  # Remove filters for broader search
                    )
                    logger.info(f"Broader search found {len(search_results)} results")
                except Exception as e:
                    logger.error(f"Broader search also failed: {e}")
                    search_results = []

            # Process enhanced results
            for result in search_results:
                # Use rerank score if available, otherwise regular score
                confidence = result.get("rerank_score", result.get("score", 0))

                # Extract metadata for easier access in UI
                metadata = result.get("metadata", {})

                match = {
                    "item_id": item.item_id,
                    "tag_code": metadata.get(
                        "item_code", item.tag_specification.tag_code
                    ),
                    "name": metadata.get(
                        "item_name", metadata.get("tag_name", "Unknown")
                    ),
                    "brand": metadata.get("brand", item.brand),
                    "matched_document": result.get("text", ""),
                    "distance": 1 - confidence,  # Convert to distance for compatibility
                    "confidence": confidence,
                    "similarity_score": confidence,  # For UI compatibility
                    "metadata": metadata,
                    "search_method": result.get("source", "unknown"),
                    "has_rerank_score": "rerank_score" in result,
                    "confidence_level": result.get("confidence_level", "unknown"),
                    "confidence_percentage": result.get("confidence_percentage", 0),
                    "type": "text",  # Mark as text-based match (not image)
                }
                all_matches.append(match)

                # Update item with best match info
                if (
                    not item.inventory_match_score
                    or confidence > item.inventory_match_score
                ):
                    item.inventory_match_score = confidence

                item.matched_inventory_items.append(match)

            # Log search performance
            logger.debug(
                f"Item {item.item_id}: {search_stats['final_results']} results "
                f"from {search_stats['semantic_candidates']} candidates"
            )

            # Also search in image collection if tag image exists
            # Check if there are image attachments for this order
            has_image_attachment = any(
                att.type == AttachmentType.IMAGE for att in (order.attachments or [])
            )

        # After processing all text searches, do visual similarity search if we have images
        if has_image_attachment:
            logger.info("Performing visual similarity search for customer images")

            # Collect paths of customer images
            customer_image_paths = []
            for att in order.attachments:
                if att.type == AttachmentType.IMAGE and att.file_path:
                    customer_image_paths.append(att.file_path)
                    logger.info(f"Using customer image: {att.filename}")

            # Get visual matches for all items
            if customer_image_paths:
                visual_matches = await self.visual_search.find_best_matches_for_order(
                    customer_image_paths, order.items, limit_per_item=5
                )

                # Track seen tag_codes to avoid duplicates across all items
                seen_tag_codes = set()

                # Add visual matches to the all_matches list
                for item_id, matches in visual_matches.items():
                    # Find the corresponding item
                    item = next((i for i in order.items if i.item_id == item_id), None)
                    if not item:
                        continue

                    for img_match in matches:
                        tag_code = img_match.get("tag_code", "")

                        # Skip if we've already added this tag_code to all_matches
                        if tag_code and tag_code in seen_tag_codes:
                            logger.debug(
                                f"Skipping duplicate tag_code {tag_code} for item {item_id}"
                            )
                            continue

                        image_match_data = {
                            "item_id": item_id,
                            "type": "image",
                            "similarity_score": img_match.get("similarity_score", 0.0),
                            "confidence": img_match.get(
                                "similarity_score", 0.0
                            ),  # Use similarity as confidence
                            "tag_code": tag_code,
                            "brand": img_match.get("brand", ""),
                            "image_path": img_match.get("image_path", ""),
                            "metadata": img_match.get("metadata", {}),
                        }
                        all_matches.append(image_match_data)

                        # Mark this tag_code as seen
                        if tag_code:
                            seen_tag_codes.add(tag_code)

                        # Update item's best match if this image match is better
                        if img_match.get("similarity_score", 0) > (
                            item.inventory_match_score or 0
                        ):
                            item.inventory_match_score = img_match.get(
                                "similarity_score", 0
                            )
                            item.best_image_match = image_match_data
                            logger.info(
                                f"Item {item_id}: Best visual match is {img_match.get('tag_code')} with {img_match.get('similarity_score', 0):.2%} similarity"
                            )

        return all_matches

    def _calculate_confidence_scores(
        self, order: ExtractedOrder, inventory_matches: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate confidence scores for each item including image similarity"""

        confidence_scores = {}

        for item in order.items:
            # Get all matches for this item
            item_matches = [
                m for m in inventory_matches if m.get("item_id") == item.item_id
            ]

            # Separate text and image matches
            text_matches = [m for m in item_matches if m.get("type") != "image"]
            image_matches = [m for m in item_matches if m.get("type") == "image"]

            # Calculate text-based confidence
            text_confidence = 0.0
            if text_matches:
                top_text_confidences = sorted(
                    [m.get("confidence", 0) for m in text_matches], reverse=True
                )[:3]
                text_confidence = sum(top_text_confidences) / len(top_text_confidences)

            # Calculate image-based confidence
            image_confidence = 0.0
            if image_matches:
                top_image_confidences = sorted(
                    [m.get("confidence", 0) for m in image_matches], reverse=True
                )[:3]
                image_confidence = sum(top_image_confidences) / len(
                    top_image_confidences
                )

            # Combine confidences with weighted average
            # If we have high image confidence (>0.85), it's a strong signal
            if image_confidence > 0.85:
                # Image match is very strong - weight it heavily
                final_confidence = text_confidence * 0.3 + image_confidence * 0.7
            elif image_confidence > 0.0:
                # We have some image match - balanced weighting
                final_confidence = text_confidence * 0.6 + image_confidence * 0.4
            else:
                # No image match - use text only
                final_confidence = text_confidence

            confidence_scores[item.item_id] = final_confidence

            # Log the confidence breakdown for debugging
            logger.debug(
                f"Item {item.item_id} confidence - Text: {text_confidence:.2f}, "
                f"Image: {image_confidence:.2f}, Final: {final_confidence:.2f}"
            )

        return confidence_scores

    def _recalculate_confidence_with_attachments(self, order: ExtractedOrder) -> float:
        """Recalculate confidence after processing attachments"""
        confidence = order.extraction_confidence

        # Boost confidence if we have successfully processed attachments
        if order.attachments:
            processed_count = sum(
                1
                for att in order.attachments
                if att.extracted_data and "error" not in att.extracted_data
            )
            if processed_count > 0:
                # Increase confidence by 10% for each successfully processed attachment
                confidence = min(1.0, confidence + (0.1 * processed_count))

                # If we extracted items from Excel, boost confidence significantly
                for att in order.attachments:
                    if att.type == AttachmentType.EXCEL and att.extracted_data:
                        if "data" in att.extracted_data and att.extracted_data["data"]:
                            confidence = min(1.0, confidence + 0.2)
                            break

        return confidence

    def _calculate_extraction_confidence(self, extracted_data: Dict[str, Any]) -> float:
        """Calculate confidence based on extraction completeness"""

        required_fields = ["customer_name", "items", "delivery_date"]
        present_fields = sum(
            1 for field in required_fields if extracted_data.get(field)
        )

        base_confidence = present_fields / len(required_fields)

        # Adjust based on item completeness
        if extracted_data.get("items"):
            item_completeness = sum(
                1
                for item in extracted_data["items"]
                if item.get("tag_code") and item.get("quantity")
            ) / len(extracted_data["items"])

            confidence = (base_confidence + item_completeness) / 2
        else:
            confidence = base_confidence * 0.5

        return min(1.0, max(0.0, confidence))

    def _determine_action(
        self, extraction_confidence: float, item_confidence_scores: Dict[str, float]
    ) -> str:
        """Determine recommended action based on confidence levels"""

        # Calculate overall confidence
        if item_confidence_scores:
            avg_item_confidence = sum(item_confidence_scores.values()) / len(
                item_confidence_scores
            )
            overall_confidence = (extraction_confidence + avg_item_confidence) / 2
        else:
            overall_confidence = extraction_confidence * 0.5

        # Apply thresholds - Only 90%+ confidence gets auto-approved
        if overall_confidence >= 0.9:
            return "auto_approve"
        else:
            # ALL orders with <90% confidence go to human review
            # Human will decide whether to approve, reject, or request clarification
            return "human_review"

    async def _auto_approve_order(self, order: ExtractedOrder) -> List[InventoryUpdate]:
        """Auto-approve order and update inventory"""

        inventory_updates = []

        # Update order status
        order.approval_status = "auto_approved"
        order.reviewed_at = datetime.now()
        order.reviewed_by = "system_auto"

        # Create inventory updates
        for item in order.items:
            if item.inventory_match_score and item.inventory_match_score >= 0.9:
                update = InventoryUpdate(
                    order_id=order.order_id,
                    item_id=item.item_id,
                    tag_code=item.tag_specification.tag_code,
                    previous_quantity=0,  # TODO: Get from database
                    quantity_used=item.quantity_ordered,
                    remaining_quantity=0,  # TODO: Calculate
                    update_type="deduction",
                    updated_by="system_auto",
                    notes="Auto-approved based on high confidence match",
                )
                inventory_updates.append(update)

                # Update item status
                item.approval_status = "approved"
                item.quantity_confirmed = item.quantity_ordered

        # Save to database
        await self._save_order_to_database(order)

        logger.info(
            f"Auto-approved order {order.order_id} with {len(inventory_updates)} inventory updates"
        )

        return inventory_updates

    async def _request_human_review(
        self, order: ExtractedOrder, inventory_matches: List[Dict[str, Any]]
    ):
        """Mark order for human review - actual review creation is handled by orchestrator"""

        # Calculate overall confidence for better context
        item_scores = [
            item.inventory_match_score
            for item in order.items
            if item.inventory_match_score
        ]
        avg_item_confidence = sum(item_scores) / len(item_scores) if item_scores else 0
        overall_confidence = (order.extraction_confidence + avg_item_confidence) / 2

        # Determine review reason based on confidence
        if overall_confidence < 0.6:
            review_reason = f"Low confidence ({overall_confidence:.1%}) - Consider requesting clarification from customer"
        elif overall_confidence < 0.8:
            review_reason = f"Medium confidence ({overall_confidence:.1%}) - Manual verification required"
        else:
            review_reason = f"High confidence ({overall_confidence:.1%}) - Final approval needed before processing"

        # Just update order status - don't create review request
        # The orchestrator will handle the actual review creation
        order.approval_status = "pending_review"

        # Store review metadata in the order for the orchestrator to use
        order.review_notes = review_reason

        # CRITICAL: Save order to database BEFORE orchestrator tries to create review
        # This ensures the foreign key reference in recommendation_queue will work
        await self._save_order_to_database(order)

        logger.info(
            f"Marked order {order.order_id} for human review (confidence: {overall_confidence:.1%}) and saved to database"
        )

    async def _request_clarification(self, order: ExtractedOrder):
        """Request clarification for low confidence orders"""

        order.approval_status = "manual_review"
        order.clarification_points = [
            "Unable to extract clear order details",
            "Please provide structured order information",
            "Include tag codes, quantities, and specifications",
        ]

        # Save order to database even when clarification is needed
        await self._save_order_to_database(order)

        # TODO: Send clarification email to customer

        logger.info(
            f"Requested clarification for order {order.order_id} and saved to database"
        )

    async def _save_order_to_database(self, order: ExtractedOrder):
        """Save order to PostgreSQL database"""

        try:
            with get_db() as session:
                # Create or get customer
                customer = (
                    session.query(Customer)
                    .filter_by(email=order.customer.email)
                    .first()
                )

                if not customer:
                    customer = Customer(
                        name=order.customer.company_name,
                        email=order.customer.email,
                        phone=order.customer.phone,
                        company=order.customer.company_name,
                    )
                    session.add(customer)
                    session.flush()

                # Create order
                db_order = Order(
                    customer_id=customer.id,
                    order_number=order.order_id,
                    status=order.approval_status,
                    total_amount=0,  # TODO: Calculate
                    # Note: created_at is set automatically by the model
                    # email_date and delivery date info can be stored in metadata or separate tables if needed
                )
                session.add(db_order)
                session.flush()

                # Create order items
                for item in order.items:
                    db_item = DBOrderItem(
                        order_id=db_order.id,
                        tag_code=item.tag_specification.tag_code,  # Fixed: was product_code
                        description=f"{item.brand} {item.tag_specification.tag_type.value}",
                        quantity=item.quantity_ordered,
                        unit_price=0,  # TODO: Calculate
                        total_price=0,  # TODO: Calculate
                    )
                    session.add(db_item)

                session.commit()
                logger.info(f"Saved order {order.order_id} to database")

        except Exception as e:
            logger.error(f"Error saving order to database: {e}")

    async def process_human_response(
        self, response: HumanReviewResponse
    ) -> OrderConfirmation:
        """Process human reviewer's response and finalize order"""

        # TODO: Implement human response processing
        pass
