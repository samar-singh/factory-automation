"""Document generation and management tools"""

import json
import logging
from datetime import datetime

from agents import function_tool

logger = logging.getLogger(__name__)


class DocumentTools:
    """Document generation and management tools"""
    
    def __init__(self, mode="execute"):
        """
        Initialize document tools
        
        Args:
            mode: "execute" for v3, "propose" for v4
        """
        self.mode = mode
    
    def create_tools(self):
        """Create and return document-related tools"""
        tools = []
        
        # Document generation tool
        @function_tool(
            name_override="generate_document",
            description_override="Generate quotations, confirmations, or other documents" if self.mode == "execute" else "Propose document generation for approval",
        )
        def generate_document(
            doc_type: str, customer_email: str, items: str, decision: str = ""
        ) -> str:
            """Generate business documents"""
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            doc_id = datetime.now().strftime("%Y%m%d-%H%M%S")
            
            if self.mode == "execute":
                # V3: Generate actual document reference
                if doc_type == "quotation":
                    return f"Generated Quotation QUO-{doc_id} for {customer_email}. Items: {items}. Valid for 7 days from {timestamp}"
                elif doc_type == "confirmation":
                    return f"Generated Order Confirmation CON-{doc_id} for {customer_email} on {timestamp}. Order: {items}"
                elif doc_type == "clarification":
                    return f"Generated Clarification Request CLA-{doc_id} for {customer_email}. Need details about: {items}"
                elif doc_type == "invoice":
                    return f"Generated Invoice INV-{doc_id} for {customer_email}. Items: {items}. Date: {timestamp}"
                else:
                    return f"Generated {doc_type} document {doc_id} for {customer_email} at {timestamp}"
            else:
                # V4: Propose document generation
                doc_content = {
                    "quotation": {
                        "title": f"Quotation QUO-{doc_id}",
                        "customer": customer_email,
                        "items": items,
                        "validity": "7 days",
                        "date": timestamp,
                        "terms": "Standard terms apply"
                    },
                    "confirmation": {
                        "title": f"Order Confirmation CON-{doc_id}",
                        "customer": customer_email,
                        "order_details": items,
                        "date": timestamp,
                        "estimated_delivery": "5-7 business days"
                    },
                    "clarification": {
                        "title": f"Clarification Request CLA-{doc_id}",
                        "customer": customer_email,
                        "questions": items,
                        "date": timestamp,
                        "response_needed_by": "48 hours"
                    },
                    "invoice": {
                        "title": f"Invoice INV-{doc_id}",
                        "customer": customer_email,
                        "items": items,
                        "date": timestamp,
                        "payment_terms": "Net 30"
                    }
                }
                
                return json.dumps({
                    "proposal": "document_generation",
                    "doc_type": doc_type,
                    "doc_id": doc_id,
                    "content": doc_content.get(doc_type, {
                        "title": f"{doc_type} {doc_id}",
                        "customer": customer_email,
                        "details": items,
                        "date": timestamp
                    }),
                    "requires_approval": True,
                    "can_be_edited": True
                })
        
        tools.append(generate_document)
        
        return tools