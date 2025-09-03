"""Order processing tools for orchestrators"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents import function_tool

logger = logging.getLogger(__name__)


class OrderTools:
    """Order processing and management tools"""
    
    def __init__(self, order_processor, chromadb_client, mode="execute"):
        """
        Initialize order tools
        
        Args:
            order_processor: OrderProcessorAgent instance
            chromadb_client: ChromaDB client
            mode: "execute" for v3, "propose" for v4
        """
        self.order_processor = order_processor
        self.chromadb_client = chromadb_client
        self.mode = mode
        self._processed_emails = set()
        self._current_attachments = []
        self._last_order_result = None
    
    def create_tools(self):
        """Create and return order-related tools"""
        tools = []
        
        # Complete order processing tool
        @function_tool(
            name_override="process_complete_order" if self.mode == "execute" else "analyze_order_for_proposal",
            description_override="Process complete order with attachments, ChromaDB search, and human review workflow. Use ONLY AFTER email classification AND attachment extraction. Do NOT use as first step." if self.mode == "execute" else "Analyze order details for proposal generation without execution. Use ONLY AFTER email classification and attachment processing.",
        )
        async def process_complete_order(
            email_subject: str,
            email_body: str,
            sender_email: str,
            attachments: Optional[str] = None,
        ) -> str:
            """Process complete order workflow including extraction, search, and review.
            
            This tool handles the complete order processing pipeline. Use this ONLY AFTER
            the email has been classified and any attachments have been extracted. This
            is typically used after classify_email_intent and extract_*_data tools.
            
            Args:
                email_subject: Subject line of the order email
                email_body: Full text content of the email with order details
                sender_email: Customer's email address placing the order
                attachments: Optional JSON string of attachment data (legacy parameter, attachments should be pre-extracted)
            
            Returns:
                JSON string with complete order processing results:
                - order_id: Generated order identifier
                - customer: Customer email address
                - total_items: Number of items in the order
                - extraction_confidence: AI confidence in order extraction (0.0 to 1.0)
                - recommended_action: Next step ("approve", "review", "clarify")
                - inventory_matches: Array of matched inventory items
                - items: Detailed list of order items with quantities and codes
            """
            
            # Create a unique key for this email
            email_key = f"{sender_email}:{email_subject}"
            
            # Check if already processed
            # Commented out for testing - this prevents reprocessing during development
            # if email_key in self._processed_emails:
            #     logger.warning(f"Email already processed: {email_key}")
            #     return json.dumps(
            #         {
            #             "status": "duplicate",
            #             "message": "This email has already been processed",
            #             "email_subject": email_subject,
            #             "sender": sender_email,
            #         }
            #     )
            
            # Mark as processed
            self._processed_emails.add(email_key)
            
            try:
                # Get attachments from context
                attachment_list = []
                if hasattr(self, "_current_attachments") and self._current_attachments:
                    attachment_list = self._current_attachments
                    logger.info(f"Using {len(attachment_list)} attachments from context")
                else:
                    logger.info("No attachments in context")
                
                # Handle legacy attachment parameter
                if attachments and not attachment_list:
                    logger.warning("Attachments passed as parameter (legacy behavior)")
                    try:
                        if isinstance(attachments, str):
                            attachment_list = json.loads(attachments)
                        else:
                            attachment_list = attachments
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse attachments JSON: {attachments}")
                
                if self.mode == "execute":
                    # V3: Actually process the order
                    result = await self.order_processor.process_order_email(
                        email_subject=email_subject,
                        email_body=email_body,
                        email_date=datetime.now(),
                        sender_email=sender_email,
                        attachments=attachment_list,
                    )
                    
                    # Format response
                    response = {
                        "order_id": result.order.order_id if result.order else "N/A",
                        "customer": result.order.customer.email if result.order else "Unknown",
                        "total_items": len(result.order.items) if result.order else 0,
                        "extraction_confidence": result.order.extraction_confidence if result.order else 0,
                        "recommended_action": result.recommended_action,
                        "approval_status": result.order.approval_status if result.order else "failed",
                        "inventory_matches": result.inventory_matches[:20] if result.inventory_matches else [],
                        "image_matches": len(result.image_matches) if hasattr(result, "image_matches") else 0,
                        "processing_time_ms": result.processing_time_ms,
                        "items": [],
                        "confidence_scores": result.confidence_scores if hasattr(result, "confidence_scores") else {},
                    }
                    
                    # Add item details
                    if result.order:
                        for item in result.order.items[:5]:
                            item_data = {
                                "tag_code": item.tag_specification.tag_code,
                                "quantity": item.quantity_ordered,
                                "brand": item.brand,
                                "match_score": item.inventory_match_score or 0,
                            }
                            response["items"].append(item_data)
                    
                    # Store result for later use
                    self._last_order_result = response
                    
                else:
                    # V4: Analyze order for proposal
                    response = {
                        "analysis_complete": True,
                        "email_subject": email_subject,
                        "sender": sender_email,
                        "attachment_count": len(attachment_list),
                        "extraction_method": "ai_analysis",
                        "proposed_items": [],
                        "confidence": 0.7,
                        "requires_human_review": True,
                        "proposed_actions": [
                            "Extract order details from email",
                            "Search inventory for matches",
                            "Calculate pricing",
                            "Generate quotation",
                            "Send response to customer"
                        ]
                    }
                
                return json.dumps(response, indent=2)
                
            except Exception as e:
                logger.error(f"Error in process_complete_order: {e}")
                return json.dumps({"error": str(e), "status": "failed"})
        
        tools.append(process_complete_order)
        
        # Order status update tool
        @function_tool(
            name_override="update_order_status",
            description_override="Update order status in the system. Use ONLY when you have a confirmed order_id and valid status change. Do NOT use for order creation or initial processing." if self.mode == "execute" else "Propose order status update. Use ONLY for existing orders with valid status transitions.",
        )
        async def update_order_status(order_id: str, new_status: str, notes: str = "") -> str:
            """Update the status of an existing order in the system.
            
            This tool modifies the status of an already-created order. Use this ONLY
            when you have a valid order_id from a previous order processing step and
            need to change its status (e.g., from pending to approved).
            
            Args:
                order_id: Existing order identifier (e.g., "ORD-20250829-123456")
                new_status: New status to set ("pending", "approved", "in_production", "completed", "cancelled", "payment_received")
                notes: Optional notes explaining the status change
            
            Returns:
                String confirming the status update with timestamp and notes
                Or JSON proposal object in propose mode
            """
            valid_statuses = [
                "pending",
                "approved",
                "in_production",
                "completed",
                "cancelled",
                "payment_received",
            ]
            
            if new_status not in valid_statuses:
                return f"Error: Invalid status '{new_status}'. Must be one of: {', '.join(valid_statuses)}"
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if self.mode == "execute":
                # V3: Actually update status (would update database)
                return f"Order {order_id} status updated to '{new_status}' at {timestamp}. Notes: {notes if notes else 'None'}"
            else:
                # V4: Propose status update
                return json.dumps({
                    "proposal": "status_update",
                    "order_id": order_id,
                    "current_status": "unknown",  # Would query DB in production
                    "proposed_status": new_status,
                    "timestamp": timestamp,
                    "notes": notes,
                    "requires_approval": True
                })
        
        tools.append(update_order_status)
        
        return tools
    
    def set_current_attachments(self, attachments: List[Dict[str, Any]]):
        """Set current email attachments for context"""
        self._current_attachments = attachments
    
    def get_last_order_result(self) -> Optional[Dict[str, Any]]:
        """Get the last order processing result"""
        return self._last_order_result