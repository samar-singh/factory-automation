"""
Workflow Models for Orchestrator Action Proposal System
Defines data structures for comprehensive workflow proposals
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class WorkflowType(str, Enum):
    """Types of workflows the system can propose"""
    NEW_ORDER = "new_order_processing"
    ORDER_CLARIFICATION = "order_clarification"
    PAYMENT_PROCESSING = "payment_processing"
    INVENTORY_INQUIRY = "inventory_inquiry"
    CUSTOMER_SERVICE = "customer_service"
    ORDER_MODIFICATION = "order_modification"
    ORDER_CANCELLATION = "order_cancellation"
    QUOTATION_REQUEST = "quotation_request"
    COMPLAINT_HANDLING = "complaint_handling"
    FOLLOW_UP = "follow_up"


class ActionType(str, Enum):
    """Types of actions that can be proposed"""
    VALIDATE_INVENTORY = "validate_inventory"
    CALCULATE_PRICING = "calculate_pricing"
    GENERATE_QUOTATION = "generate_quotation"
    COMPOSE_EMAIL = "compose_email"
    UPDATE_DATABASE = "update_database"
    RESERVE_INVENTORY = "reserve_inventory"
    SCHEDULE_FOLLOWUP = "schedule_followup"
    CREATE_ORDER = "create_order"
    REQUEST_INFORMATION = "request_information"
    SEND_CATALOG = "send_catalog"
    ESCALATE_TO_MANAGER = "escalate_to_manager"
    GENERATE_INVOICE = "generate_invoice"
    UPDATE_PAYMENT = "update_payment"
    CANCEL_ORDER = "cancel_order"
    MODIFY_ORDER = "modify_order"


class RiskLevel(str, Enum):
    """Risk levels for proposed actions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(str, Enum):
    """Status of workflow approval"""
    PENDING = "pending"
    APPROVED = "approved"
    APPROVED_WITH_CHANGES = "approved_with_changes"
    REJECTED = "rejected"
    PARTIALLY_APPROVED = "partially_approved"


class CustomerTier(str, Enum):
    """Customer classification tiers"""
    PREMIUM = "premium"
    REGULAR = "regular"
    NEW = "new"
    INACTIVE = "inactive"
    VIP = "vip"


class DatabaseOperation(BaseModel):
    """Represents a database operation within an action"""
    type: str = Field(..., description="Type of database operation")
    table: str = Field(..., description="Database table to operate on")
    data: Dict[str, Any] = Field(..., description="Data for the operation")
    rollback_query: Optional[str] = Field(None, description="Query to rollback this operation")


class EmailContent(BaseModel):
    """Email content to be sent"""
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Email body content")
    attachments: List[str] = Field(default_factory=list, description="List of attachment filenames")
    cc: List[str] = Field(default_factory=list, description="CC recipients")
    bcc: List[str] = Field(default_factory=list, description="BCC recipients")
    is_html: bool = Field(False, description="Whether email body is HTML")
    template_used: Optional[str] = Field(None, description="Template name if used")


class ProposedAction(BaseModel):
    """Represents a single action in the workflow"""
    step: int = Field(..., description="Step number in the workflow")
    action: ActionType = Field(..., description="Type of action to perform")
    details: str = Field(..., description="Human-readable description of the action")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score for this action")
    risk: RiskLevel = Field(..., description="Risk level of this action")
    data: Dict[str, Any] = Field(default_factory=dict, description="Action-specific data")
    
    # Optional fields for specific action types
    content: Optional[Any] = Field(None, description="Content to be generated (email, document)")
    editable: bool = Field(True, description="Whether human can edit this action")
    preview_url: Optional[str] = Field(None, description="URL to preview generated content")
    database_operations: List[DatabaseOperation] = Field(
        default_factory=list, 
        description="Database operations for this action"
    )
    
    # Execution tracking
    approved: bool = Field(False, description="Whether this action is approved")
    modified: bool = Field(False, description="Whether this action was modified by human")
    executed: bool = Field(False, description="Whether this action has been executed")
    execution_result: Optional[Dict[str, Any]] = Field(None, description="Result of execution")
    execution_error: Optional[str] = Field(None, description="Error if execution failed")


class AlternativeAction(BaseModel):
    """Alternative actions that could be taken"""
    action: str = Field(..., description="Alternative action description")
    reason: str = Field(..., description="Why this alternative might be considered")
    confidence: float = Field(..., ge=0, le=1, description="Confidence in this alternative")
    impact: str = Field(..., description="Expected impact of choosing this alternative")


class RiskAssessment(BaseModel):
    """Risk assessment for the workflow"""
    risk: str = Field(..., description="Risk identifier")
    description: str = Field(..., description="Description of the risk")
    likelihood: str = Field(..., description="Likelihood of risk occurring")
    impact: str = Field(..., description="Impact if risk occurs")
    mitigation: str = Field(..., description="How to mitigate this risk")
    risk_level: RiskLevel = Field(..., description="Overall risk level")


class WorkflowAnalysis(BaseModel):
    """Analysis results that led to the workflow proposal"""
    email_classification: str = Field(..., description="Type of email received")
    customer_context: Dict[str, Any] = Field(..., description="Customer history and context")
    inventory_matches: List[Dict[str, Any]] = Field(
        default_factory=list, 
        description="Inventory items found"
    )
    confidence_metrics: Dict[str, float] = Field(..., description="Various confidence scores")
    risk_assessment: List[RiskAssessment] = Field(
        default_factory=list, 
        description="Identified risks"
    )
    extracted_requirements: Dict[str, Any] = Field(
        default_factory=dict,
        description="Requirements extracted from email"
    )


class ProposedWorkflow(BaseModel):
    """Complete workflow proposal for human review"""
    workflow_id: str = Field(..., description="Unique identifier for this workflow")
    workflow_type: WorkflowType = Field(..., description="Type of workflow")
    confidence: float = Field(..., ge=0, le=1, description="Overall confidence in this workflow")
    customer_tier: CustomerTier = Field(..., description="Customer classification")
    estimated_value: Optional[float] = Field(None, description="Estimated order value")
    
    # Core components
    analysis: WorkflowAnalysis = Field(..., description="Analysis that led to this proposal")
    proposed_actions: List[ProposedAction] = Field(..., description="Sequence of actions to take")
    reasoning: str = Field(..., description="Explanation of why this workflow was chosen")
    alternatives: List[AlternativeAction] = Field(
        default_factory=list, 
        description="Alternative approaches"
    )
    risks: List[RiskAssessment] = Field(
        default_factory=list, 
        description="Risks identified"
    )
    
    # Content to be generated
    email_content: Optional[EmailContent] = Field(None, description="Email to be sent")
    documents_to_generate: List[str] = Field(
        default_factory=list, 
        description="Documents to create"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now, description="When proposal was created")
    created_by: str = Field("orchestrator_v3", description="System that created the proposal")
    
    # Approval tracking
    approval_status: ApprovalStatus = Field(
        ApprovalStatus.PENDING, 
        description="Current approval status"
    )
    approved_by: Optional[str] = Field(None, description="Who approved the workflow")
    approved_at: Optional[datetime] = Field(None, description="When it was approved")
    approval_notes: Optional[str] = Field(None, description="Notes from approver")
    
    # Execution tracking
    execution_started_at: Optional[datetime] = Field(None, description="When execution began")
    execution_completed_at: Optional[datetime] = Field(None, description="When execution completed")
    execution_status: Optional[str] = Field(None, description="Current execution status")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class WorkflowExecutionResult(BaseModel):
    """Result of executing a workflow"""
    workflow_id: str = Field(..., description="ID of the executed workflow")
    success: bool = Field(..., description="Whether execution was successful")
    executed_actions: List[str] = Field(..., description="Actions that were executed")
    failed_action: Optional[str] = Field(None, description="Action that failed if any")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    rollback_performed: bool = Field(False, description="Whether rollback was performed")
    execution_time: float = Field(..., description="Total execution time in seconds")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Outputs from execution")


class WorkflowModification(BaseModel):
    """Tracks modifications made to a proposed workflow"""
    action_step: int = Field(..., description="Which action step was modified")
    field_modified: str = Field(..., description="What field was changed")
    original_value: Any = Field(..., description="Original proposed value")
    new_value: Any = Field(..., description="Human-modified value")
    reason: Optional[str] = Field(None, description="Reason for modification")
    modified_by: str = Field(..., description="Who made the modification")
    modified_at: datetime = Field(default_factory=datetime.now, description="When modified")


class WorkflowTemplate(BaseModel):
    """Template for common workflow patterns"""
    template_id: str = Field(..., description="Unique template identifier")
    workflow_type: WorkflowType = Field(..., description="Type of workflow this template is for")
    name: str = Field(..., description="Human-friendly template name")
    description: str = Field(..., description="What this template does")
    base_actions: List[Dict[str, Any]] = Field(..., description="Base actions in template")
    customizable_fields: List[str] = Field(
        default_factory=list,
        description="Fields that can be customized"
    )
    conditions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Conditions for using this template"
    )
    
    
class WorkflowMetrics(BaseModel):
    """Metrics for tracking workflow performance"""
    workflow_id: str = Field(..., description="Workflow being tracked")
    proposal_generation_time: float = Field(..., description="Time to generate proposal (seconds)")
    review_time: Optional[float] = Field(None, description="Time spent in review (seconds)")
    execution_time: Optional[float] = Field(None, description="Time to execute (seconds)")
    actions_proposed: int = Field(..., description="Number of actions proposed")
    actions_approved: int = Field(0, description="Number of actions approved")
    actions_modified: int = Field(0, description="Number of actions modified")
    confidence_score: float = Field(..., description="Overall confidence score")
    user_satisfaction: Optional[int] = Field(None, description="User rating (1-5)")