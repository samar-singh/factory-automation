"""Advanced Order Processor Agent with full workflow integration"""

import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from openai import AsyncOpenAI

from ..factory_config.settings import settings
from ..factory_database.connection import get_db
from ..factory_database.models import Customer, Order
from ..factory_database.models import OrderItem as DBOrderItem
from ..factory_database.vector_db import ChromaDBClient
from ..factory_models.order_models import (
    Attachment,
    AttachmentType,
    CustomerInfo,
    DeliveryInfo,
    ExtractedOrder,
    FitTagMapping,
    HumanReviewRequest,
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

            return OrderProcessingResult(
                order=extracted_order,
                inventory_matches=inventory_matches,
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
           - Tag types (fit tags, main tags, etc.)
           - Quantities
           - Remarks/special requirements
           - Fit mappings if mentioned
        3. Proforma invoice details if mentioned
        4. Delivery requirements and urgency
        5. Any brand information (Allen Solly, Myntra, etc.)
        
        Pay special attention to:
        - Tables showing fit-to-tag mappings
        - Product codes and SKUs
        - Sustainability or special tag requirements
        - Delivery dates
        
        Return as structured JSON matching the ExtractedOrder schema.
        """

        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert at extracting structured order information from garment industry emails.
                        Focus on tag codes, fit mappings, quantities, and special requirements.
                        Always return valid JSON matching the provided schema.""",
                    },
                    {"role": "user", "content": extraction_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=3000,
            )

            extracted_data = json.loads(response.choices[0].message.content)

            # Parse into Pydantic model
            order_items = []
            for item_data in extracted_data.get("items", []):
                # Create TagSpecification
                tag_spec = TagSpecification(
                    tag_code=item_data.get("tag_code", "UNKNOWN"),
                    tag_type=TagType(item_data.get("tag_type", "other")),
                    quantity=item_data.get("quantity", 0),
                    color=item_data.get("color"),
                    size=item_data.get("size"),
                    material=(
                        Material(item_data.get("material", "other"))
                        if item_data.get("material")
                        else None
                    ),
                    remarks=item_data.get("remarks"),
                )

                # Create FitTagMapping if present
                fit_mapping = None
                if item_data.get("fit_mapping"):
                    fit_data = item_data["fit_mapping"]
                    fit_mapping = FitTagMapping(
                        fit_type=fit_data.get("fit_type", ""),
                        fit_tag_codes=fit_data.get("fit_tag_codes", []),
                        main_tag_code=fit_data.get("main_tag_code", ""),
                        main_tag_remark=fit_data.get("main_tag_remark"),
                    )

                # Create OrderItem
                order_item = OrderItem(
                    item_id=f"ITEM-{len(order_items)+1:03d}",
                    tag_specification=tag_spec,
                    brand=item_data.get(
                        "brand", extracted_data.get("brand", "Unknown")
                    ),
                    category=item_data.get("category"),
                    fit_mapping=fit_mapping,
                    quantity_ordered=item_data.get("quantity", 0),
                )

                order_items.append(order_item)

            # Create customer info
            customer = CustomerInfo(
                company_name=extracted_data.get("customer_name", "Unknown"),
                contact_person=extracted_data.get("contact_person"),
                email=sender_email,
                phone=extracted_data.get("phone"),
            )

            # Create delivery info
            delivery = DeliveryInfo(
                required_date=(
                    datetime.fromisoformat(extracted_data["delivery_date"])
                    if extracted_data.get("delivery_date")
                    else None
                ),
                urgency=OrderPriority(extracted_data.get("urgency", "normal")),
                special_instructions=extracted_data.get("special_instructions"),
            )

            # Create proforma invoice if present
            proforma = None
            if extracted_data.get("proforma_invoice"):
                invoice_data = extracted_data["proforma_invoice"]
                proforma = ProformaInvoice(
                    invoice_number=invoice_data.get("number", "Unknown"),
                    invoice_date=(
                        datetime.fromisoformat(invoice_data["date"])
                        if invoice_data.get("date")
                        else None
                    ),
                )

            # Calculate extraction confidence
            confidence = self._calculate_extraction_confidence(extracted_data)

            # Create ExtractedOrder
            extracted_order = ExtractedOrder(
                email_subject=email_subject,
                email_date=email_date,
                customer=customer,
                items=order_items,
                proforma_invoice=proforma,
                purchase_order_number=extracted_data.get("po_number"),
                delivery=delivery,
                extraction_confidence=confidence,
                extraction_method="ai_gpt4",
                missing_information=extracted_data.get("missing_information", []),
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
            content = att.get("content")  # Base64 or bytes

            # Determine attachment type
            if filename.endswith((".xlsx", ".xls")):
                att_type = AttachmentType.EXCEL
                # Process Excel file
                extracted_data = await self._process_excel_attachment(content, filename)
            elif filename.endswith((".jpg", ".jpeg", ".png", ".gif")):
                att_type = AttachmentType.IMAGE
                # Process image with Qwen2.5VL
                extracted_data = await self._process_image_attachment(
                    content, filename, order.order_id, order.customer.company_name
                )
            elif filename.endswith(".pdf"):
                att_type = AttachmentType.PDF
                extracted_data = await self._process_pdf_attachment(content, filename)
            elif filename.endswith((".doc", ".docx")):
                att_type = AttachmentType.WORD
                extracted_data = await self._process_word_attachment(content, filename)
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
        self, content: bytes, filename: str, order_id: str, customer_name: str
    ) -> Dict[str, Any]:
        """Process image attachment using Qwen2.5VL and store in ChromaDB"""

        try:
            # Save image temporarily
            with tempfile.NamedTemporaryFile(
                suffix=Path(filename).suffix, delete=False
            ) as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name

            # Process and store in ChromaDB
            result = await self.image_processor.process_and_store_image(
                image_path=tmp_path,
                order_id=order_id,
                customer_name=customer_name,
                additional_metadata={
                    "original_filename": filename,
                    "source": "email_attachment",
                },
            )

            # Clean up temp file
            Path(tmp_path).unlink()

            return result

        except Exception as e:
            logger.error(f"Error processing image attachment: {e}")
            return {"error": str(e)}

    async def _process_excel_attachment(
        self, content: bytes, filename: str
    ) -> Dict[str, Any]:
        """Process Excel attachment to extract order data"""

        try:
            # Save temporarily and read with pandas
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_path = tmp_file.name

            # Read Excel file
            df = pd.read_excel(tmp_path)

            # Extract relevant data
            extracted_data = {
                "filename": filename,
                "rows": len(df),
                "columns": list(df.columns),
                "data": df.to_dict(orient="records"),
            }

            # Clean up
            Path(tmp_path).unlink()

            return extracted_data

        except Exception as e:
            logger.error(f"Error processing Excel attachment: {e}")
            return {"error": str(e)}

    async def _process_pdf_attachment(
        self, content: bytes, filename: str
    ) -> Dict[str, Any]:
        """Process PDF attachment"""
        # TODO: Implement PDF processing with OCR if needed
        return {"filename": filename, "type": "pdf", "status": "not_implemented"}

    async def _process_word_attachment(
        self, content: bytes, filename: str
    ) -> Dict[str, Any]:
        """Process Word document attachment"""
        # TODO: Implement Word document processing
        return {"filename": filename, "type": "word", "status": "not_implemented"}

    async def _search_inventory_for_items(
        self, order: ExtractedOrder
    ) -> List[Dict[str, Any]]:
        """Search inventory using enhanced search with reranking"""

        all_matches = []

        for item in order.items:
            # Create search query from item details
            search_query = f"{item.brand} {item.tag_specification.tag_code} {item.tag_specification.tag_type.value}"

            # Add additional context to query
            if item.tag_specification.color:
                search_query += f" {item.tag_specification.color}"
            if item.tag_specification.material:
                search_query += f" {item.tag_specification.material}"

            # Use enhanced search with reranking
            search_results, search_stats = self.enhanced_search.search(
                query=search_query,
                n_results=5,
                n_candidates=20,  # Get more candidates for reranking
                filters={"brand": item.brand} if item.brand else None,
            )

            # Process enhanced results
            for result in search_results:
                # Use rerank score if available, otherwise regular score
                confidence = result.get("rerank_score", result.get("score", 0))

                match = {
                    "item_id": item.item_id,
                    "tag_code": item.tag_specification.tag_code,
                    "matched_document": result.get("text", ""),
                    "distance": 1 - confidence,  # Convert to distance for compatibility
                    "confidence": confidence,
                    "metadata": result.get("metadata", {}),
                    "search_method": result.get("source", "unknown"),
                    "has_rerank_score": "rerank_score" in result,
                    "confidence_level": result.get("confidence_level", "unknown"),
                    "confidence_percentage": result.get("confidence_percentage", 0),
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
            image_matches = await self.image_processor.search_similar_images(
                search_query, limit=3
            )

            for img_match in image_matches:
                all_matches.append(
                    {
                        "item_id": item.item_id,
                        "type": "image",
                        "image_hash": img_match["image_hash"],
                        "confidence": img_match["similarity_score"],
                        "analysis": img_match["analysis"],
                    }
                )

        return all_matches

    def _calculate_confidence_scores(
        self, order: ExtractedOrder, inventory_matches: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate confidence scores for each item"""

        confidence_scores = {}

        for item in order.items:
            # Get matches for this item
            item_matches = [
                m for m in inventory_matches if m.get("item_id") == item.item_id
            ]

            if item_matches:
                # Average confidence of top matches
                top_confidences = sorted(
                    [m.get("confidence", 0) for m in item_matches], reverse=True
                )[:3]
                avg_confidence = sum(top_confidences) / len(top_confidences)
            else:
                avg_confidence = 0.0

            confidence_scores[item.item_id] = avg_confidence

        return confidence_scores

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
        """Request human review for medium confidence orders"""

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

        # Create review request
        HumanReviewRequest(
            order_id=order.order_id,
            order=order,
            review_reason=review_reason,
            confidence_score=overall_confidence * 100,  # Convert to percentage
            suggested_matches=inventory_matches[:10],  # Top 10 matches
            clarification_needed=[
                f"Verify {item.tag_specification.tag_code} (match: {item.inventory_match_score:.1%})"
                for item in order.items
                if item.inventory_match_score and item.inventory_match_score < 0.9
            ],
            priority=(
                OrderPriority.HIGH
                if order.delivery.urgency == OrderPriority.URGENT
                else OrderPriority.MEDIUM
            ),
        )

        # Submit to human interaction manager
        if self.human_manager:
            # Prepare email data as dict
            email_data_dict = {
                "message_id": order.order_id,
                "from": order.customer.email,
                "subject": order.email_subject,
                "body": f"Order from {order.customer.company_name}",
            }

            # Prepare search results as list
            search_results_list = []
            for match in inventory_matches[:5]:
                search_results_list.append(
                    {
                        "item_id": match.get("item_id", ""),
                        "tag_code": match.get("tag_code", ""),
                        "confidence": match.get("confidence", 0),
                        "metadata": match.get("metadata", {}),
                    }
                )

            # Prepare extracted items as list
            extracted_items_list = []
            for item in order.items[:5]:
                extracted_items_list.append(
                    {
                        "item_id": item.item_id,
                        "tag_code": item.tag_specification.tag_code,
                        "quantity": item.quantity_ordered,
                        "tag_type": item.tag_specification.tag_type.value,
                    }
                )

            await self.human_manager.create_review_request(
                email_data=email_data_dict,
                search_results=search_results_list,
                confidence_score=overall_confidence,
                extracted_items=extracted_items_list,
            )

        # Update order status
        order.approval_status = "pending_review"

        logger.info(f"Submitted order {order.order_id} for human review")

    async def _request_clarification(self, order: ExtractedOrder):
        """Request clarification for low confidence orders"""

        order.approval_status = "manual_review"
        order.clarification_points = [
            "Unable to extract clear order details",
            "Please provide structured order information",
            "Include tag codes, quantities, and specifications",
        ]

        # TODO: Send clarification email to customer

        logger.info(f"Requested clarification for order {order.order_id}")

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
                    order_date=order.email_date,
                    delivery_date=order.delivery.required_date,
                )
                session.add(db_order)
                session.flush()

                # Create order items
                for item in order.items:
                    db_item = DBOrderItem(
                        order_id=db_order.id,
                        product_code=item.tag_specification.tag_code,
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
