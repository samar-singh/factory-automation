"""
Factory automation models for order processing and workflow orchestration

This package contains:
- order_models: Business domain models for orders, customers, and inventory
- workflow_models: Orchestration models for proposals and workflow management
"""

# Business domain models (existing system)
from .order_models import (
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
    SpecialRequirement,
    TagSpecification,
    TagType,
    QueuedRecommendation,
    BatchOperation,
    RecommendationType,
)

# Workflow and proposal models (new system)
try:
    from .workflow_models import (
        # Core workflow models
        ProposedWorkflow,
        ProposedAction,
        WorkflowAnalysis,
        WorkflowExecutionResult,
        
        # Supporting models
        AlternativeAction,
        RiskAssessment,
        EmailContent,
        DatabaseOperation,
        WorkflowModification,
        WorkflowTemplate,
        WorkflowMetrics,
        
        # Enums
        WorkflowType,
        ActionType,
        RiskLevel,
        ApprovalStatus,
        CustomerTier,
    )
    workflow_models_available = True
except ImportError:
    workflow_models_available = False

__all__ = [
    # Order models
    "ExtractedOrder",
    "OrderItem",
    "CustomerInfo",
    "DeliveryInfo",
    "TagSpecification",
    "FitTagMapping",
    "Attachment",
    "AttachmentType",
    "OrderPriority",
    "TagType",
    "Material",
    "ProformaInvoice",
    "InventoryUpdate",
    "OrderProcessingResult",
    "HumanReviewRequest",
    "HumanReviewResponse",
    "OrderConfirmation",
    "SpecialRequirement",
    "QueuedRecommendation",
    "BatchOperation",
    "RecommendationType",
]

# Add workflow models to __all__ if available
if workflow_models_available:
    __all__.extend([
        "ProposedWorkflow",
        "ProposedAction",
        "WorkflowAnalysis",
        "WorkflowExecutionResult",
        "AlternativeAction",
        "RiskAssessment",
        "EmailContent",
        "DatabaseOperation",
        "WorkflowModification",
        "WorkflowTemplate",
        "WorkflowMetrics",
        "WorkflowType",
        "ActionType",
        "RiskLevel",
        "ApprovalStatus",
        "CustomerTier",
    ])
