"""
Validation rules for tool execution order and dependencies.
Defines which tools must be called first and their dependencies.
"""

from typing import Dict, List, Optional
from enum import Enum

class ToolCategory(Enum):
    """Categories of tools for validation purposes"""
    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    PROCESSING = "processing"
    SEARCH = "search"
    RESPONSE = "response"
    DECISION = "decision"

# Core validation rules
VALIDATION_RULES = {
    # Email Classification - MUST BE FIRST
    "classify_email_intent": {
        "must_be_first": True,
        "dependencies": [],
        "category": ToolCategory.CLASSIFICATION,
        "required_params": ["email_subject", "email_body", "sender_email"],
        "description": "Email classification must always be performed first"
    },
    
    # Attachment Processing - Requires classification
    "extract_pdf_data": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.EXTRACTION,
        "required_params": ["filename"],
        "optional_params": ["content"],
        "description": "PDF extraction requires email classification first"
    },
    
    "extract_excel_data": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.EXTRACTION,
        "required_params": ["filename"],
        "optional_params": ["content"],
        "description": "Excel extraction requires email classification first"
    },
    
    "process_tag_image": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.EXTRACTION,
        "required_params": ["image_path"],
        "description": "Image processing requires email classification first"
    },
    
    # Order Processing - Requires classification
    "process_complete_order": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.PROCESSING,
        "required_params": ["email_data"],
        "conditional_dependencies": {
            "if_has_attachments": ["extract_pdf_data", "extract_excel_data"]
        },
        "description": "Order processing requires classification and attachment extraction"
    },
    
    # Search Operations - Can be done after classification
    "search_inventory": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.SEARCH,
        "required_params": ["query"],
        "description": "Inventory search requires classification"
    },
    
    "search_visual": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.SEARCH,
        "required_params": ["image_data"],
        "description": "Visual search requires classification"
    },
    
    # Customer Context - Can be done after classification
    "get_customer_context": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.SEARCH,
        "required_params": ["customer_email"],
        "description": "Customer context requires classification"
    },
    
    # Document Generation - Requires processing
    "generate_document": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent", "process_complete_order"],
        "category": ToolCategory.RESPONSE,
        "required_params": ["document_type", "order_data"],
        "description": "Document generation requires order processing"
    },
    
    # Email Response - Should be last
    "send_email_response": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.RESPONSE,
        "should_be_last": True,
        "required_params": ["to_email", "subject", "body"],
        "description": "Email response should be sent after all processing"
    },
    
    # Payment Tracking
    "track_payment": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.PROCESSING,
        "required_params": ["payment_info"],
        "description": "Payment tracking requires classification"
    },
    
    # Order Status Updates
    "update_order_status": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.PROCESSING,
        "required_params": ["order_id", "status"],
        "description": "Order updates require classification"
    },
    
    # Supplier Handling
    "handle_supplier_inquiry": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent"],
        "category": ToolCategory.PROCESSING,
        "required_params": ["supplier_email", "inquiry_type", "email_subject", "email_body"],
        "description": "Supplier inquiries require classification"
    },
    
    # Human Review Creation
    "create_human_review": {
        "must_be_first": False,
        "dependencies": ["classify_email_intent", "process_complete_order"],
        "category": ToolCategory.DECISION,
        "required_params": ["order_id", "reason"],
        "description": "Human review requires order processing"
    },
    
    # Check emails - Can be first for email monitoring
    "check_emails": {
        "must_be_first": False,  # Can be first when monitoring
        "dependencies": [],  # No dependencies for checking emails
        "category": ToolCategory.EXTRACTION,
        "required_params": [],
        "description": "Check for new emails in inbox"
    }
}

# Workflow patterns for different email types
WORKFLOW_PATTERNS = {
    "NEW_ORDER": [
        "classify_email_intent",
        "extract_pdf_data",  # if attachments
        "extract_excel_data",  # if attachments
        "process_complete_order",
        "search_inventory",
        "generate_document",
        "send_email_response"
    ],
    "ORDER_MODIFICATION": [
        "classify_email_intent",
        "get_customer_context",
        "update_order_status",
        "send_email_response"
    ],
    "PAYMENT": [
        "classify_email_intent",
        "track_payment",
        "update_order_status",
        "send_email_response"
    ],
    "INQUIRY": [
        "classify_email_intent",
        "get_customer_context",
        "search_inventory",
        "send_email_response"
    ],
    "QUOTATION_REQUEST": [
        "classify_email_intent",
        "search_inventory",
        "generate_document",
        "send_email_response"
    ],
    "SUPPLIER": [
        "classify_email_intent",
        "handle_supplier_inquiry",
        "send_email_response"
    ],
    "COMPLAINT": [
        "classify_email_intent",
        "get_customer_context",
        "create_human_review",
        "send_email_response"
    ],
    "FOLLOWUP": [
        "classify_email_intent",
        "get_customer_context",
        "update_order_status",
        "send_email_response"
    ]
}

# Tool aliases for flexibility
TOOL_ALIASES = {
    "classify_intent": "classify_email_intent",
    "extract_pdf": "extract_pdf_data",
    "extract_excel": "extract_excel_data",
    "process_order": "process_complete_order",
    "search": "search_inventory",
    "send_email": "send_email_response",
    "get_customer": "get_customer_context"
}

def get_tool_rule(tool_name: str) -> Optional[Dict]:
    """
    Get validation rule for a tool, checking aliases.
    
    Args:
        tool_name: Name of the tool (or alias)
        
    Returns:
        Validation rule dict or None if not found
    """
    # Check if it's an alias
    actual_name = TOOL_ALIASES.get(tool_name, tool_name)
    return VALIDATION_RULES.get(actual_name)

def get_workflow_pattern(email_type: str) -> List[str]:
    """
    Get suggested workflow pattern for an email type.
    
    Args:
        email_type: Type of email (NEW_ORDER, PAYMENT, etc.)
        
    Returns:
        List of tool names in suggested order
    """
    return WORKFLOW_PATTERNS.get(email_type, [])