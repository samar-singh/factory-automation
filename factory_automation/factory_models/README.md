# Factory Models Directory

This directory contains Pydantic models for the Factory Automation system. The models are organized into two main categories:

## Model Files

### 1. `order_models.py` - Business Domain Models
**Purpose**: Contains domain-specific data models for factory automation business logic

**Key Models**:
- `ExtractedOrder` - Orders extracted from customer emails
- `OrderItem` - Individual items with tag specifications
- `CustomerInfo` - Customer and company information
- `OrderProcessingResult` - Results from order processing
- `HumanReviewRequest/Response` - Human review workflow data
- `QueuedRecommendation` - Recommendations queued for review
- `BatchOperation` - Batch processing of multiple items
- `TagSpecification` - Detailed tag requirements
- `InventoryUpdate` - Inventory change tracking

**Used By**: Order processing agents, inventory management, human review system

### 2. `workflow_models.py` - Orchestration & Proposal Models
**Purpose**: Contains models for the proposal-based orchestration architecture

**Key Models**:
- `ProposedWorkflow` - Complete workflow proposal for human review
- `ProposedAction` - Individual actions within a workflow
- `WorkflowAnalysis` - Analysis that leads to workflow proposals
- `WorkflowExecutionResult` - Results from executing approved workflows
- `AlternativeAction` - Alternative approaches to consider
- `RiskAssessment` - Risk analysis for proposed actions
- `WorkflowTemplate` - Reusable workflow patterns
- `EmailContent` - Structured email content for proposals

**Used By**: Proposal engine, orchestrator (when in proposal mode), workflow executor

### 3. `ai_extraction_models.py` - AI Integration Models
**Purpose**: Models for AI-based data extraction and processing

**Key Models**:
- Models for GPT-4 extraction
- Image analysis results
- Multimodal processing data

## Architecture Overview

```
Customer Email
    ↓
[AI Extraction] → ExtractedOrder (order_models)
    ↓
[Proposal Engine] → ProposedWorkflow (workflow_models)
    ↓
[Human Review] → Approved Actions
    ↓
[Execution] → OrderProcessingResult (order_models)
```

## Model Relationships

- `ProposedWorkflow` references `ExtractedOrder` for order data
- `WorkflowAnalysis` uses inventory matches from order processing
- Both model sets work together in the complete pipeline

## Usage Guidelines

1. **For new features**:
   - Business data → Add to `order_models.py`
   - Workflow/orchestration → Add to `workflow_models.py`

2. **Import conventions**:
   ```python
   # Business domain models
   from factory_automation.factory_models.order_models import (
       ExtractedOrder, OrderItem, CustomerInfo
   )
   
   # Workflow/proposal models
   from factory_automation.factory_models.workflow_models import (
       ProposedWorkflow, ProposedAction, WorkflowType
   )
   ```

3. **Model validation**:
   - All models use Pydantic for automatic validation
   - Custom validators are defined where needed
   - Enums ensure type safety for categorical data

## Migration Notes

The system is transitioning from direct execution (using only `order_models`) to a proposal-based system (using both model sets). During this transition:

- Existing code continues to use `order_models.py`
- New proposal system uses both model files
- No breaking changes to existing functionality
- Gradual migration path available

## Testing

Test files for models:
- `test_order_models.py` - Tests business domain models
- `test_workflow_models.py` - Tests proposal system models
- `test_model_integration.py` - Tests interaction between model sets