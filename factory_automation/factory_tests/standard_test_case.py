#!/usr/bin/env python3
"""
Standard Test Case for Integration Testing
This email and attachment scenario will be used for all phase testing
to ensure consistency and track behavior changes across implementations.
"""

from datetime import datetime
from typing import Dict, Any, List

# Standard test email content
TEST_EMAIL = {
    "message_id": "test-integration-001",
    "from": "trimsblr@yahoo.co.in",
    "to": "storerhppl@gmail.com",
    "subject": "Re: Allen Solly Order - Pro-Forma Invoice #1542",
    "body": """Dear Sir/Madam
Order received with thanks & Greetings from Interface Direct.   
PFA Pro-Forma Invoice # 1542 & please check the description of the tag image & approve the order & do the needful. Please let us know if you need any more help.

 

With warm Regards,

PUSHPARAJ.A/ Interface Direct/ Tag supplier / trimsblr@yahoo.co.in
Dispatches Team / PH/998000 9355.


On Monday 28 July, 2025 at 07:00:31 pm IST, Rajlaxmi Home Products Pvt ltd <storerhppl@gmail.com> wrote:


Dear Meena ji,

See attached Allen Solly (E-com) brand bulk tag po copy for order confirmation .We need the bulk tag materials delivery date  

Fit    FIT TAG    Main Tag    Main Tag Remark
Bootcut    TBALWBL0009N/10N/11N/12N/13N/14N/15N/16N    TBALHGT0033N    Sustainability hangtag
Classic straight    TBALWBL0001N/02N/03N/04N/05N/06N/07N/08N    TBALHGT0033N    Sustainability hangtag
Skinny    TBALTAG0363N/364N/365N/366N/367N/368N/369N    TBALHGT0033N    Sustainability hangtag
Slim    TBALWBL0060N/61N/62N/63N/64N/65N/66N/67N/68N    TBALHGT0033N    Sustainability hangtag

Pls confirm the receipt and revert back .

Thanks & Regards,
Vijay kapse
RAJLAXMI  HOME PRODUCTS PVT. LTD
Gala No. 5, Anjani Kumar Indi. Estate ,
Datta Mandir Road, Bhandup ( W)
Mumbai-400078
Contact No. 8655233004""",
    "timestamp": datetime.now().isoformat(),
    "attachments": [
        {
            "filename": "Allen_Solly_PO.xlsx",
            "path": "/Users/samarsingh/Downloads/Allen solly",
            "type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        }
    ]
}

# Expected behaviors for each phase
PHASE_EXPECTATIONS = {
    "phase_3": {
        "description": "Action tracking only - no execution changes",
        "expected_actions": [
            "analyze_email",
            "search_inventory", 
            "extract_excel_data",
            "calculate_price",
            "create_proforma_invoice",
            "send_email_response"
        ],
        "auto_executed": [],  # Phase 3 doesn't change execution
        "pending_approval": [],  # Phase 3 doesn't implement approval
        "tracked_in_audit": True,
        "workflow_id_generated": True
    },
    "phase_4": {
        "description": "Two-tier execution - auto-execute reversible, queue irreversible",
        "expected_actions": [
            "analyze_email",
            "search_inventory",
            "extract_excel_data", 
            "calculate_price",
            "create_proforma_invoice",
            "send_email_response"
        ],
        "auto_executed": [
            "analyze_email",  # Reversible
            "search_inventory",  # Reversible
            "extract_excel_data",  # Reversible
            "calculate_price"  # Reversible
        ],
        "pending_approval": [
            "create_proforma_invoice",  # Irreversible (document generation)
            "send_email_response"  # Irreversible (customer communication)
        ],
        "tracked_in_audit": True,
        "workflow_id_generated": True
    },
    "phase_5": {
        "description": "UI shows two-tier actions with color coding",
        "ui_changes": {
            "green_bullets": ["analyze_email", "search_inventory", "extract_excel_data", "calculate_price"],
            "orange_bullets": ["create_proforma_invoice", "send_email_response"],
            "expandable_email_preview": True,
            "approve_reject_buttons": True
        }
    },
    "phase_6": {
        "description": "Approval flow implementation",
        "approval_workflow": {
            "can_approve": True,
            "can_reject": True,
            "can_modify_email": True,
            "status_updates": True,
            "loading_states": True
        }
    }
}

# Key items to extract from email
EXPECTED_EXTRACTIONS = {
    "customer": "Rajlaxmi Home Products Pvt ltd",
    "customer_email": "storerhppl@gmail.com", 
    "supplier": "Interface Direct",
    "supplier_email": "trimsblr@yahoo.co.in",
    "invoice_number": "1542",
    "items": [
        {
            "fit": "Bootcut",
            "fit_tags": ["TBALWBL0009N", "TBALWBL0010N", "TBALWBL0011N", "TBALWBL0012N", 
                        "TBALWBL0013N", "TBALWBL0014N", "TBALWBL0015N", "TBALWBL0016N"],
            "main_tag": "TBALHGT0033N",
            "remark": "Sustainability hangtag"
        },
        {
            "fit": "Classic straight",
            "fit_tags": ["TBALWBL0001N", "TBALWBL0002N", "TBALWBL0003N", "TBALWBL0004N",
                        "TBALWBL0005N", "TBALWBL0006N", "TBALWBL0007N", "TBALWBL0008N"],
            "main_tag": "TBALHGT0033N",
            "remark": "Sustainability hangtag"
        },
        {
            "fit": "Skinny",
            "fit_tags": ["TBALTAG0363N", "TBALTAG0364N", "TBALTAG0365N", "TBALTAG0366N",
                        "TBALTAG0367N", "TBALTAG0368N", "TBALTAG0369N"],
            "main_tag": "TBALHGT0033N",
            "remark": "Sustainability hangtag"
        },
        {
            "fit": "Slim",
            "fit_tags": ["TBALWBL0060N", "TBALWBL0061N", "TBALWBL0062N", "TBALWBL0063N",
                        "TBALWBL0064N", "TBALWBL0065N", "TBALWBL0066N", "TBALWBL0067N", "TBALWBL0068N"],
            "main_tag": "TBALHGT0033N",
            "remark": "Sustainability hangtag"
        }
    ],
    "brand": "Allen Solly",
    "order_type": "bulk_tag_order",
    "requires_delivery_date": True
}

# Actions that should be classified as irreversible
IRREVERSIBLE_ACTIONS_IN_FLOW = [
    "send_email_response",  # Sends email to customer
    "send_customer_email",  # Alternative email sending
    "create_proforma_invoice",  # Creates official document
    "reserve_inventory_final",  # Commits inventory
    "process_payment",  # Financial transaction
    "update_order_status_to_confirmed"  # Business state change
]

# Actions that should be classified as reversible
REVERSIBLE_ACTIONS_IN_FLOW = [
    "analyze_email",  # Just analysis
    "search_inventory",  # Read-only search
    "extract_excel_data",  # Data extraction
    "extract_pdf_data",  # Data extraction
    "calculate_price",  # Calculation
    "validate_tag_codes",  # Validation
    "check_inventory_availability",  # Check only
    "generate_draft_response"  # Draft creation
]


def get_test_email() -> Dict[str, Any]:
    """Get the standard test email for integration testing"""
    return TEST_EMAIL.copy()


def get_expected_behavior(phase: str) -> Dict[str, Any]:
    """Get expected behavior for a specific phase"""
    return PHASE_EXPECTATIONS.get(phase, {})


def validate_action_classification(action_name: str, action_type: str) -> bool:
    """Validate if an action is correctly classified"""
    if action_name in IRREVERSIBLE_ACTIONS_IN_FLOW:
        return action_type == "irreversible"
    elif action_name in REVERSIBLE_ACTIONS_IN_FLOW:
        return action_type == "reversible"
    return True  # Unknown actions pass by default


def get_formatted_email_for_ui() -> str:
    """Get the email formatted for pasting into the UI textbox"""
    return f"""From: {TEST_EMAIL['from']}
To: {TEST_EMAIL['to']}
Subject: {TEST_EMAIL['subject']}
Date: {datetime.now().strftime('%Y-%m-%d')}

{TEST_EMAIL['body']}"""


# Test assertions for each phase
def assert_phase_3_behavior(result: Dict[str, Any]) -> List[str]:
    """Validate Phase 3 implementation"""
    errors = []
    
    # Check workflow ID generation
    if not result.get('workflow_id'):
        errors.append("Workflow ID not generated")
    elif not result['workflow_id'].startswith('WF-'):
        errors.append(f"Invalid workflow ID format: {result['workflow_id']}")
    
    # Check action tracking
    if result.get('actions_tracked', 0) == 0:
        errors.append("No actions tracked in audit log")
    
    return errors


def assert_phase_4_behavior(result: Dict[str, Any]) -> List[str]:
    """Validate Phase 4 implementation"""
    errors = []
    
    # Check auto-execution of reversible actions
    auto_executed = result.get('auto_executed_actions', [])
    for action in PHASE_EXPECTATIONS['phase_4']['auto_executed']:
        if action not in auto_executed:
            errors.append(f"Reversible action '{action}' not auto-executed")
    
    # Check queuing of irreversible actions
    pending = result.get('pending_approval_actions', [])
    for action in PHASE_EXPECTATIONS['phase_4']['pending_approval']:
        if action not in pending:
            errors.append(f"Irreversible action '{action}' not queued for approval")
    
    return errors


def assert_phase_5_behavior(ui_state: Dict[str, Any]) -> List[str]:
    """Validate Phase 5 UI implementation"""
    errors = []
    
    expected_ui = PHASE_EXPECTATIONS['phase_5']['ui_changes']
    
    # Check for green bullets (executed actions)
    if not ui_state.get('has_green_bullets'):
        errors.append("UI doesn't show green bullets for executed actions")
    
    # Check for orange bullets (pending actions)
    if not ui_state.get('has_orange_bullets'):
        errors.append("UI doesn't show orange bullets for pending actions")
    
    # Check for expandable email preview
    if not ui_state.get('has_expandable_email'):
        errors.append("UI doesn't have expandable email preview")
    
    # Check for approve/reject buttons
    if not ui_state.get('has_approval_buttons'):
        errors.append("UI doesn't have approve/reject/modify buttons")
    
    return errors