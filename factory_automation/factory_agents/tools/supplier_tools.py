"""Supplier and vendor management tools"""

import json
import logging
from datetime import datetime

from agents import function_tool

logger = logging.getLogger(__name__)


class SupplierTools:
    """Supplier and vendor communication tools"""
    
    def __init__(self, mode="execute"):
        """
        Initialize supplier tools
        
        Args:
            mode: "execute" for v3, "propose" for v4
        """
        self.mode = mode
    
    def create_tools(self):
        """Create and return supplier-related tools"""
        tools = []
        
        # Handle supplier inquiry tool
        @function_tool(
            name_override="handle_supplier_inquiry",
            description_override="Handle supplier communications, vendor inquiries, and procurement-related emails." if self.mode == "execute" else "Analyze supplier communication for proposal generation",
        )
        async def handle_supplier_inquiry(
            supplier_email: str, inquiry_type: str, email_subject: str, email_body: str
        ) -> str:
            """Handle supplier communications"""
            
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
                
                if self.mode == "execute":
                    # V3: Actually handle inquiry
                    result = {
                        "success": True,
                        "inquiry_processed": True,
                        "inquiry_record": inquiry_record,
                        "routed_to": route_to,
                        "auto_response_sent": True,
                        "response_message": f"Your {inquiry_types.get(inquiry_type, 'inquiry')} has been received and forwarded to our {route_to.replace('_', ' ')}. We will respond within 24 hours.",
                        "requires_human_review": inquiry_type in ["quality_concern", "new_vendor"],
                        "confidence": 0.85,
                    }
                    
                    logger.info(
                        f"Supplier inquiry processed: {inquiry_type} from {supplier_email}, routed to {route_to}"
                    )
                else:
                    # V4: Propose handling
                    result = {
                        "proposal": "supplier_inquiry_handling",
                        "inquiry_analysis": inquiry_record,
                        "proposed_routing": route_to,
                        "proposed_actions": [
                            {
                                "action": "acknowledge_receipt",
                                "details": f"Send acknowledgment to {supplier_email}"
                            },
                            {
                                "action": "route_to_team",
                                "details": f"Forward to {route_to}"
                            },
                            {
                                "action": "create_ticket",
                                "details": f"Create tracking ticket {inquiry_record['inquiry_id']}"
                            },
                            {
                                "action": "set_reminder",
                                "details": "Set 24-hour response reminder"
                            }
                        ],
                        "priority": inquiry_record["priority"],
                        "requires_approval": inquiry_type in ["quality_concern", "new_vendor"],
                        "estimated_resolution": "24-48 hours"
                    }
                
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
        
        return tools