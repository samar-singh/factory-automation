"""Pydantic models for order data extraction and processing"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, validator


class OrderPriority(str, Enum):
    """Order priority levels"""

    URGENT = "urgent"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NORMAL = "normal"


class TagType(str, Enum):
    """Types of tags/labels"""

    PRICE_TAG = "price_tag"
    HANG_TAG = "hang_tag"
    CARE_LABEL = "care_label"
    BRAND_LABEL = "brand_label"
    SIZE_LABEL = "size_label"
    FIT_TAG = "fit_tag"
    MAIN_TAG = "main_tag"
    SUSTAINABILITY_TAG = "sustainability_tag"
    BARCODE_STICKER = "barcode_sticker"
    WOVEN_LABEL = "woven_label"
    PRINTED_LABEL = "printed_label"
    OTHER = "other"


class Material(str, Enum):
    """Material types for tags"""

    PAPER = "paper"
    CARDBOARD = "cardboard"
    PLASTIC = "plastic"
    FABRIC = "fabric"
    WOVEN = "woven"
    SYNTHETIC = "synthetic"
    RECYCLED = "recycled"
    OTHER = "other"


class AttachmentType(str, Enum):
    """Types of attachments"""

    EXCEL = "excel"
    IMAGE = "image"
    PDF = "pdf"
    WORD = "word"
    CSV = "csv"
    OTHER = "other"


class Attachment(BaseModel):
    """Model for email attachments"""

    filename: str
    type: AttachmentType
    size_bytes: Optional[int] = None
    mime_type: Optional[str] = None
    content: Optional[bytes] = None  # For small files
    file_path: Optional[str] = None  # For saved files
    extracted_data: Optional[Dict[str, Any]] = None  # Processed content


class SpecialRequirement(BaseModel):
    """Special requirements for tags"""

    requirement_type: str  # e.g., "embossing", "foiling", "special_finish"
    description: str
    additional_cost: Optional[Decimal] = None


class TagSpecification(BaseModel):
    """Detailed tag specifications"""

    tag_code: str  # e.g., "TBALWBL0009N"
    tag_type: TagType
    quantity: int
    color: Optional[str] = None
    size: Optional[str] = None  # e.g., "2x3 inches"
    material: Optional[Material] = None
    finish: Optional[str] = None  # e.g., "matte", "glossy"
    special_requirements: List[SpecialRequirement] = []
    unit_price: Optional[Decimal] = None
    remarks: Optional[str] = None

    @validator("quantity")
    def quantity_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be positive")
        return v


class FitTagMapping(BaseModel):
    """Mapping between fit types and tag codes (specific to garment industry)"""

    fit_type: str  # e.g., "Bootcut", "Skinny", "Slim"
    fit_tag_codes: List[str]  # e.g., ["TBALWBL0009N", "TBALWBL0010N"]
    main_tag_code: str  # e.g., "TBALHGT0033N"
    main_tag_remark: Optional[str] = None  # e.g., "Sustainability hangtag"


class CustomerInfo(BaseModel):
    """Customer/Sender information"""

    company_name: str
    contact_person: Optional[str] = None
    email: str
    phone: Optional[str] = None
    address: Optional[str] = None
    customer_code: Optional[str] = None  # Internal customer code


class DeliveryInfo(BaseModel):
    """Delivery requirements"""

    required_date: Optional[datetime] = None
    urgency: OrderPriority = OrderPriority.NORMAL
    delivery_address: Optional[str] = None
    special_instructions: Optional[str] = None


class ProformaInvoice(BaseModel):
    """Proforma invoice details"""

    invoice_number: str
    invoice_date: Optional[datetime] = None
    total_amount: Optional[Decimal] = None
    currency: str = "INR"
    payment_terms: Optional[str] = None


class OrderItem(BaseModel):
    """Individual order item with all details"""

    item_id: str  # Unique identifier for the item
    tag_specification: TagSpecification
    brand: str  # e.g., "Allen Solly"
    category: Optional[str] = None  # e.g., "E-com", "Retail"
    fit_mapping: Optional[FitTagMapping] = None
    quantity_ordered: int
    quantity_confirmed: Optional[int] = None
    inventory_match_score: Optional[float] = None  # ChromaDB match score
    matched_inventory_items: List[Dict[str, Any]] = []  # ChromaDB results
    best_image_match: Optional[Dict[str, Any]] = None  # Best visual match
    approval_status: Literal["pending", "approved", "rejected", "review_required"] = (
        "pending"
    )
    approval_notes: Optional[str] = None


class ExtractedOrder(BaseModel):
    """Complete extracted order data"""

    # Order identification
    order_id: str = Field(
        default_factory=lambda: f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    email_subject: str
    email_date: datetime

    # Customer information
    customer: CustomerInfo

    # Order details
    items: List[OrderItem]
    total_items: int = 0
    total_quantity: int = 0

    # Invoice details
    proforma_invoice: Optional[ProformaInvoice] = None
    purchase_order_number: Optional[str] = None

    # Delivery information
    delivery: DeliveryInfo

    # Attachments
    attachments: List[Attachment] = []

    # Processing metadata
    extraction_confidence: float = Field(ge=0, le=1)  # 0 to 1
    extraction_method: str  # e.g., "ai_gpt4", "manual", "hybrid"
    extracted_at: datetime = Field(default_factory=datetime.now)
    missing_information: List[str] = []
    requires_clarification: bool = False
    clarification_points: List[str] = []

    # Approval workflow
    approval_status: Literal[
        "auto_approved", "pending_review", "manual_review", "rejected"
    ] = "pending_review"
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None

    @validator("total_items", always=True)
    def calculate_total_items(cls, v, values):
        if "items" in values:
            return len(values["items"])
        return v

    @validator("total_quantity", always=True)
    def calculate_total_quantity(cls, v, values):
        if "items" in values:
            return sum(item.quantity_ordered for item in values["items"])
        return v

    @validator("approval_status", always=True)
    def determine_approval_status(cls, v, values):
        """Determine approval status based on confidence threshold"""
        if "extraction_confidence" in values:
            confidence = values["extraction_confidence"]
            if confidence >= 0.8:
                return "auto_approved"
            elif confidence >= 0.6:
                return "pending_review"
            else:
                return "manual_review"
        return v


class InventoryUpdate(BaseModel):
    """Model for inventory updates after order approval"""

    order_id: str
    item_id: str
    tag_code: str
    previous_quantity: int
    quantity_used: int
    remaining_quantity: int
    update_type: Literal["deduction", "addition", "adjustment"]
    updated_at: datetime = Field(default_factory=datetime.now)
    updated_by: str
    notes: Optional[str] = None


class OrderProcessingResult(BaseModel):
    """Result of order processing"""

    order: ExtractedOrder
    inventory_matches: List[Dict[str, Any]]  # ChromaDB search results
    image_matches: List[Dict[str, Any]] = []  # Visual similarity matches
    confidence_scores: Dict[str, float]  # Item-wise confidence scores
    recommended_action: Literal["auto_approve", "human_review", "request_clarification"]
    inventory_updates: List[InventoryUpdate] = []
    processing_time_ms: int
    errors: List[str] = []
    warnings: List[str] = []


class HumanReviewRequest(BaseModel):
    """Request for human review"""

    order_id: str
    order: ExtractedOrder
    review_reason: str
    confidence_score: float
    suggested_matches: List[Dict[str, Any]]
    clarification_needed: List[str]
    priority: OrderPriority
    created_at: datetime = Field(default_factory=datetime.now)
    deadline: Optional[datetime] = None


class HumanReviewResponse(BaseModel):
    """Human reviewer's response"""

    order_id: str
    reviewer_name: str
    decision: Literal["approved", "rejected", "request_clarification"]
    approved_items: List[str] = []  # List of approved item_ids
    rejected_items: List[str] = []  # List of rejected item_ids
    modifications: Dict[str, Any] = {}  # Any modifications to order
    clarification_request: Optional[str] = None
    notes: str
    reviewed_at: datetime = Field(default_factory=datetime.now)
    inventory_updates_approved: bool = True


class OrderConfirmation(BaseModel):
    """Final order confirmation after approval"""

    order_id: str
    confirmation_number: str
    customer: CustomerInfo
    approved_items: List[OrderItem]
    total_amount: Decimal
    estimated_delivery_date: datetime
    payment_terms: str
    special_instructions: Optional[str] = None
    inventory_updated: bool = False
    inventory_updates: List[InventoryUpdate] = []
    confirmed_at: datetime = Field(default_factory=datetime.now)
    confirmed_by: str


class RecommendationType(str, Enum):
    """Types of recommendations for queue system"""

    EMAIL_RESPONSE = "email_response"
    DOCUMENT_GENERATION = "document_generation"
    INVENTORY_UPDATE = "inventory_update"
    DATABASE_UPDATE = "database_update"
    NEW_ITEM_ADDITION = "new_item_addition"
    CUSTOMER_FOLLOW_UP = "customer_follow_up"


class QueuedRecommendation(BaseModel):
    """Recommendation queued for human review"""

    queue_id: str = Field(
        default_factory=lambda: f"QUEUE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{datetime.now().microsecond:06d}"
    )
    order_id: Optional[str] = (
        None  # Optional for recommendations not tied to specific orders
    )
    customer_email: str
    recommendation_type: RecommendationType
    recommendation_data: Dict[str, Any]  # Flexible JSON data
    confidence_score: float = Field(ge=0, le=1)
    priority: OrderPriority = OrderPriority.MEDIUM
    status: Literal[
        "pending", "in_review", "approved", "rejected", "executed", "failed"
    ] = "pending"
    batch_id: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    executed_at: Optional[datetime] = None

    # Results
    execution_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class BatchOperation(BaseModel):
    """Batch of recommendations for processing"""

    batch_id: str = Field(
        default_factory=lambda: f"BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    )
    batch_name: Optional[str] = None
    batch_type: Literal["daily", "manual", "urgent", "scheduled"] = "manual"

    # Items
    total_items: int = 0
    queue_items: List[QueuedRecommendation] = []
    approved_items: List[str] = []  # queue_ids
    rejected_items: List[str] = []  # queue_ids
    modified_items: Dict[str, Dict[str, Any]] = {}  # queue_id -> modifications

    # Status
    status: Literal[
        "pending", "in_review", "processing", "completed", "failed", "rolled_back"
    ] = "pending"

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    executed_at: Optional[datetime] = None
    executed_by: Optional[str] = None
    completed_at: Optional[datetime] = None

    # Results
    execution_time_ms: Optional[int] = None
    results: Optional[Dict[str, Any]] = None
    error_log: List[str] = []
    rollback_available: bool = True
    rollback_executed_at: Optional[datetime] = None
