"""Payment tracking and processing tools"""

import json
import logging
import re
from datetime import datetime
from typing import Optional

from agents import function_tool

logger = logging.getLogger(__name__)


class PaymentTools:
    """Payment tracking and management tools"""
    
    def __init__(self, mode="execute"):
        """
        Initialize payment tools
        
        Args:
            mode: "execute" for v3, "propose" for v4
        """
        self.mode = mode
    
    def create_tools(self):
        """Create and return payment-related tools"""
        tools = []
        
        # Payment tracking tool
        @function_tool(
            name_override="track_payment",
            description_override="Track and process payment confirmations including UTR numbers, cheque details, and payment receipts." if self.mode == "execute" else "Analyze payment information for proposal generation",
        )
        async def track_payment(
            sender_email: str,
            payment_type: str,  # "utr", "cheque", "cash", "online"
            payment_reference: str,
            amount: Optional[float] = None,
            order_id: Optional[str] = None,
        ) -> str:
            """Track payment information"""
            
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
                
                if self.mode == "execute":
                    # V3: Actually track payment
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
                        "requires_human_review": payment_type == "cheque" or (amount and amount > 100000),
                    }
                else:
                    # V4: Propose payment tracking
                    result = {
                        "proposal": "payment_tracking",
                        "payment_analysis": {
                            "sender": sender_email,
                            "type": payment_type,
                            "reference": payment_reference,
                            "amount": amount,
                            "order_id": order_id,
                            "validation": "passed" if payment_type != "utr" or re.match(r"^\d{12,22}$", payment_reference) else "failed"
                        },
                        "proposed_actions": [
                            {
                                "action": "verify_payment",
                                "details": f"Verify {payment_type} payment with reference {payment_reference}"
                            },
                            {
                                "action": "update_order_status",
                                "details": f"Update order {order_id or 'TBD'} to payment_received"
                            },
                            {
                                "action": "send_confirmation",
                                "details": f"Send payment confirmation to {sender_email}"
                            }
                        ],
                        "requires_approval": True,
                        "risk_level": "high" if payment_type == "cheque" else "low"
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
        
        return tools