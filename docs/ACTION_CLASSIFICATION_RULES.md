# Action Classification Rules
**Phase 2 - Two-Tier Action System**  
**Plan ID**: PLAN-2025-01-TWOTIER  
**Created**: 2025-01-23  

## Overview

The Action Classification System categorizes all orchestrator actions into two types:
1. **REVERSIBLE**: Can be undone, safe to auto-execute
2. **IRREVERSIBLE**: Cannot be undone, requires human approval

## Core Principle

> Any action that creates an external commitment, sends communication to customers/suppliers, or affects financial transactions MUST require human approval.

## Classification Rules

### 🔴 IRREVERSIBLE Actions (Require Human Approval)

These actions create permanent changes or external commitments:

#### Customer Communications
- `send_email_response` - Sends email to customer
- `send_customer_email` - Any customer email
- `send_order_confirmation` - Order confirmation emails
- `send_invoice` - Invoice delivery
- `send_quotation` - Quotation delivery
- `send_rejection_notice` - Order rejection notices

#### Inventory Commitments
- `reserve_inventory_final` - Final inventory reservation
- `commit_inventory` - Permanent inventory commitment
- `deduct_inventory` - Reduce available stock
- `block_inventory` - Block stock for order

#### Financial Operations
- `process_payment` - Process any payment
- `create_official_invoice` - Generate legal invoice
- `send_payment_receipt` - Send payment confirmation
- `issue_refund` - Process refunds

#### Order State Changes (External Impact)
- `confirm_order` - Confirm order to customer
- `ship_order` - Mark order as shipped
- `cancel_order_with_notification` - Cancel with customer notification

#### Supplier Operations
- `send_supplier_order` - Send orders to suppliers
- `notify_supplier` - Any supplier notification
- `confirm_supplier_shipment` - Confirm supplier shipments

### ✅ REVERSIBLE Actions (Can Auto-Execute)

These actions are safe to execute automatically:

#### Analysis & Search Operations
- `analyze_email` - Parse and understand emails
- `extract_order_data` - Extract order information
- `search_inventory` - Search product database
- `calculate_price` - Price calculations
- `validate_quantities` - Quantity validation
- `check_availability` - Stock availability checks

#### Internal Database Operations
- `create_draft_order` - Create draft orders
- `update_order_status_internal` - Internal status updates
- `save_customer_info` - Store customer data
- `log_activity` - Activity logging
- `update_metadata` - Metadata updates

#### Document Generation (Not Sending)
- `generate_quotation` - Create quotation documents
- `generate_invoice_draft` - Create invoice drafts
- `create_email_draft` - Prepare email drafts
- `prepare_report` - Generate reports

#### AI/ML Operations
- `process_with_gpt` - GPT processing
- `analyze_image_with_ai` - Image analysis
- `extract_text_from_pdf` - PDF text extraction
- `generate_embeddings` - Create embeddings

## Heuristic Classification

When an action is not in the explicit lists, the system uses keyword-based heuristics:

### Irreversible Keywords
Actions containing these keywords are classified as IRREVERSIBLE:
- `send`, `email`, `sms`, `notify`
- `confirm`, `commit`, `reserve`, `block`
- `payment`, `invoice`, `ship`, `cancel`
- `supplier`, `customer`, `external`

### Reversible Keywords
Actions containing these keywords are classified as REVERSIBLE:
- `search`, `find`, `get`, `fetch`, `read`
- `calculate`, `validate`, `check`, `analyze`
- `generate`, `create`, `draft`, `prepare`
- `update`, `save`, `log`, `cache`

### Default Behavior
**When uncertain, the system defaults to IRREVERSIBLE for safety.**

## Implementation Details

### Files
- **Classifier**: `factory_automation/factory_agents/action_classifier.py`
- **Integration**: `factory_automation/factory_agents/tools/tool_factory.py`
- **Tests**: `factory_automation/factory_tests/test_action_classifier.py`

### Usage Example

```python
from factory_automation.factory_agents.action_classifier import ActionClassifier

classifier = ActionClassifier()

# Check if action requires approval
if classifier.is_irreversible("send_email_response"):
    print("This action requires human approval")
    
# Get full requirements
requirements = classifier.get_action_requirements("send_email_response")
print(f"Requires approval: {requirements['requires_approval']}")
print(f"Can auto-execute: {requirements['can_auto_execute']}")
print(f"Risk level: {requirements['risk_level']}")
```

### Tool Factory Integration

The `ToolFactory` automatically classifies all tools:

```python
from factory_automation.factory_agents.tools.tool_factory import ToolFactory

factory = ToolFactory(mode="execute")

# Check tool classification
if factory.is_tool_irreversible("send_email_response"):
    # Queue for approval
    pass
else:
    # Execute immediately
    pass

# Get summary of all tools
summary = factory.get_tool_classifications_summary()
print(f"Reversible tools: {summary['total_reversible']}")
print(f"Irreversible tools: {summary['total_irreversible']}")
```

## Testing

Run tests with:
```bash
pytest factory_automation/factory_tests/test_action_classifier.py -v
```

## Safety Considerations

1. **Conservative Default**: Unknown actions default to IRREVERSIBLE
2. **No Email Without Approval**: All email sending requires human confirmation
3. **Financial Protection**: All payment operations require approval
4. **Inventory Guard**: Final inventory commitments need confirmation
5. **Audit Trail**: All classifications are logged for review

## Modification Guidelines

To add or modify classifications:

1. Update the appropriate list in `ActionClassifier` class
2. Add corresponding test case
3. Document the change in this file
4. Run tests to verify

**IMPORTANT**: Never move email sending or payment actions to reversible without explicit business approval.

## Statistics

Current classification counts:
- **Irreversible Actions**: 20+ defined
- **Reversible Actions**: 20+ defined
- **Heuristic Coverage**: ~95% of common actions

---

This classification system ensures that critical business actions always have human oversight while allowing safe operations to proceed automatically for efficiency.