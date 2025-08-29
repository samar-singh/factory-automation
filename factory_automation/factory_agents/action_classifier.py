"""
Action Classification System for Two-Tier Execution
Phase 2 - PLAN-2025-01-TWOTIER

Categorizes actions as reversible or irreversible based on business impact.
Irreversible actions require human approval before execution.
"""

from enum import Enum
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Classification of action reversibility"""
    REVERSIBLE = "reversible"      # Can be undone/rolled back
    IRREVERSIBLE = "irreversible"  # Cannot be undone, requires approval


class ActionCategory(Enum):
    """Categories of actions in the system"""
    # Analysis and Search (Safe)
    AI_ANALYSIS = "ai_analysis"
    IMAGE_ANALYSIS = "image_analysis"
    INVENTORY_SEARCH = "inventory_search"
    DATABASE_READ = "database_read"
    FILE_READ = "file_read"
    CALCULATION = "calculation"
    
    # Internal Updates (Reversible)
    DATABASE_WRITE = "database_write"
    FILE_GENERATE = "file_generate"
    CACHE_UPDATE = "cache_update"
    
    # External Communications (Irreversible)
    EMAIL_SEND = "email_send"
    SMS_SEND = "sms_send"
    
    # Business Commitments (Irreversible)
    INVENTORY_RESERVE = "inventory_reserve"
    INVENTORY_COMMIT = "inventory_commit"
    ORDER_CONFIRM = "order_confirm"
    
    # Financial (Irreversible)
    PAYMENT_PROCESS = "payment_process"
    INVOICE_SEND = "invoice_send"
    
    # Supplier Operations (Irreversible)
    SUPPLIER_ORDER = "supplier_order"
    SUPPLIER_NOTIFY = "supplier_notify"


class ActionClassifier:
    """
    Classifies actions based on their reversibility and business impact.
    Core principle: Any action that creates external commitments or 
    communications requires human approval.
    """
    
    # Define irreversible actions - these ALWAYS require human approval
    IRREVERSIBLE_ACTIONS = {
        # Customer communications
        "send_email_response",
        "send_customer_email", 
        "send_order_confirmation",
        "send_invoice",
        "send_quotation",
        "send_rejection_notice",
        
        # Inventory commitments
        "reserve_inventory_final",
        "commit_inventory",
        "deduct_inventory",
        "block_inventory",
        
        # Financial operations
        "process_payment",
        "create_official_invoice",
        "send_payment_receipt",
        "issue_refund",
        
        # Order state changes (external impact)
        "confirm_order",
        "ship_order",
        "cancel_order_with_notification",
        
        # Supplier operations
        "send_supplier_order",
        "notify_supplier",
        "confirm_supplier_shipment",
    }
    
    # Define reversible actions - these can auto-execute
    REVERSIBLE_ACTIONS = {
        # Analysis operations
        "analyze_email",
        "classify_email_intent",  # Just classifying, not sending
        "extract_order_data",
        "search_inventory",
        "calculate_price",
        "validate_quantities",
        "check_availability",
        
        # Data extraction (read-only operations)
        "extract_excel_data",
        "extract_pdf_data",
        "extract_csv_data",
        "extract_image_data",
        "parse_attachment",
        "read_attachment_content",
        
        # Internal database operations
        "create_draft_order",
        "update_order_status_internal",
        "save_customer_info",
        "log_activity",
        "update_metadata",
        
        # Document generation (not sending)
        "generate_quotation",
        "generate_invoice_draft",
        "create_email_draft",
        "prepare_report",
        
        # AI/ML operations
        "process_with_gpt",
        "analyze_image_with_ai",
        "extract_text_from_pdf",
        "generate_embeddings",
        
        # Cache and search operations
        "update_search_index",
        "refresh_cache",
        "store_embeddings",
    }
    
    def __init__(self):
        """Initialize the action classifier"""
        self.classification_cache: Dict[str, ActionType] = {}
        logger.info(f"Initialized ActionClassifier with {len(self.IRREVERSIBLE_ACTIONS)} irreversible actions")
    
    def classify_action(self, action_name: str, category: Optional[ActionCategory] = None) -> ActionType:
        """
        Classify an action as reversible or irreversible.
        
        Args:
            action_name: Name of the action/tool
            category: Optional category for additional context
            
        Returns:
            ActionType.REVERSIBLE or ActionType.IRREVERSIBLE
        """
        # Check cache first
        if action_name in self.classification_cache:
            return self.classification_cache[action_name]
        
        # Check explicit lists
        if action_name in self.IRREVERSIBLE_ACTIONS:
            classification = ActionType.IRREVERSIBLE
        elif action_name in self.REVERSIBLE_ACTIONS:
            classification = ActionType.REVERSIBLE
        else:
            # Use heuristics if not in explicit lists
            classification = self._classify_by_heuristics(action_name, category)
        
        # Cache the result
        self.classification_cache[action_name] = classification
        
        logger.debug(f"Classified '{action_name}' as {classification.value}")
        return classification
    
    def _classify_by_heuristics(self, action_name: str, category: Optional[ActionCategory]) -> ActionType:
        """
        Use heuristics to classify actions not in explicit lists.
        Default to IRREVERSIBLE for safety when uncertain.
        """
        action_lower = action_name.lower()
        
        # Check for keywords indicating irreversible actions
        irreversible_keywords = [
            "send", "email", "sms", "notify",
            "confirm", "commit", "reserve", "block",
            "payment", "invoice", "ship", "cancel",
            "supplier", "customer", "external"
        ]
        
        for keyword in irreversible_keywords:
            if keyword in action_lower:
                logger.info(f"Classified '{action_name}' as IRREVERSIBLE based on keyword '{keyword}'")
                return ActionType.IRREVERSIBLE
        
        # Check for keywords indicating reversible actions
        reversible_keywords = [
            "search", "find", "get", "fetch", "read",
            "calculate", "validate", "check", "analyze",
            "generate", "create", "draft", "prepare",
            "update", "save", "log", "cache"
        ]
        
        for keyword in reversible_keywords:
            if keyword in action_lower:
                logger.info(f"Classified '{action_name}' as REVERSIBLE based on keyword '{keyword}'")
                return ActionType.REVERSIBLE
        
        # Check category if provided
        if category:
            if category in [
                ActionCategory.EMAIL_SEND,
                ActionCategory.SMS_SEND,
                ActionCategory.INVENTORY_RESERVE,
                ActionCategory.INVENTORY_COMMIT,
                ActionCategory.ORDER_CONFIRM,
                ActionCategory.PAYMENT_PROCESS,
                ActionCategory.INVOICE_SEND,
                ActionCategory.SUPPLIER_ORDER,
                ActionCategory.SUPPLIER_NOTIFY,
            ]:
                return ActionType.IRREVERSIBLE
        
        # Default to IRREVERSIBLE for safety
        logger.warning(f"Could not classify '{action_name}' with certainty, defaulting to IRREVERSIBLE for safety")
        return ActionType.IRREVERSIBLE
    
    def is_irreversible(self, action_name: str) -> bool:
        """Check if an action is irreversible and requires approval"""
        return self.classify_action(action_name) == ActionType.IRREVERSIBLE
    
    def is_reversible(self, action_name: str) -> bool:
        """Check if an action is reversible and can auto-execute"""
        return self.classify_action(action_name) == ActionType.REVERSIBLE
    
    def get_action_requirements(self, action_name: str) -> Dict[str, any]:
        """
        Get detailed requirements for an action.
        
        Returns:
            Dictionary with action requirements and metadata
        """
        action_type = self.classify_action(action_name)
        
        return {
            "action_name": action_name,
            "type": action_type.value,
            "requires_approval": action_type == ActionType.IRREVERSIBLE,
            "can_auto_execute": action_type == ActionType.REVERSIBLE,
            "can_rollback": action_type == ActionType.REVERSIBLE,
            "risk_level": "high" if action_type == ActionType.IRREVERSIBLE else "low",
        }
    
    def bulk_classify(self, action_names: List[str]) -> Dict[str, ActionType]:
        """
        Classify multiple actions at once.
        
        Args:
            action_names: List of action names to classify
            
        Returns:
            Dictionary mapping action names to their types
        """
        return {
            action: self.classify_action(action)
            for action in action_names
        }
    
    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about action classifications"""
        return {
            "total_irreversible": len(self.IRREVERSIBLE_ACTIONS),
            "total_reversible": len(self.REVERSIBLE_ACTIONS),
            "total_classified": len(self.classification_cache),
            "cached_irreversible": sum(
                1 for t in self.classification_cache.values() 
                if t == ActionType.IRREVERSIBLE
            ),
            "cached_reversible": sum(
                1 for t in self.classification_cache.values()
                if t == ActionType.REVERSIBLE
            ),
        }


# Singleton instance for use across the application
action_classifier = ActionClassifier()