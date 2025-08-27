#!/usr/bin/env python3
"""
Test email approval flow by directly requesting email sending
"""

import asyncio
import json
from datetime import datetime
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_agents.orchestrator_v3_agentic import AgenticOrchestratorV3

async def test_email_approval():
    """Test that email sending requires approval"""
    
    print("\n" + "="*70)
    print("🧪 TESTING EMAIL APPROVAL FLOW")
    print("="*70)
    
    # Initialize orchestrator
    print("\n🚀 Initializing orchestrator...")
    chromadb_client = ChromaDBClient()
    orchestrator = AgenticOrchestratorV3(chromadb_client, use_mock_gmail=False)
    
    # Create an email that explicitly asks for a response to be sent
    test_email = {
        "message_id": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "from": "customer@example.com",
        "to": "orders@factory.com",
        "subject": "URGENT: Need quotation for Allen Solly tags",
        "body": """Dear Factory,

We urgently need a quotation for the following Allen Solly tags:
- TBALWBL0001N - 1000 pieces
- TBALWBL0002N - 1500 pieces  
- TBALWBL0003N - 2000 pieces

Please send us the quotation immediately with pricing and availability.
This is urgent as we need to place the order today.

IMPORTANT: Please acknowledge this email and send the quotation to our email address.

Best regards,
Customer Corp
""",
        "timestamp": datetime.now().isoformat(),
        "attachments": []
    }
    
    print("\n📧 Processing email:")
    print(f"  Subject: {test_email['subject']}")
    print("  Key instruction: 'Please acknowledge this email and send the quotation'")
    
    # Process the email
    print("\n⚙️ Processing...")
    result = await orchestrator.process_email(test_email)
    
    print("\n📊 Results:")
    print(f"  Success: {result.get('success')}")
    print(f"  Workflow ID: {result.get('workflow_id')}")
    print(f"  Tool calls: {len(result.get('tool_calls', []))}")
    
    # Check for auto-executed vs pending approval
    auto_executed = result.get('auto_executed_actions', [])
    pending_approval = result.get('pending_approval_actions', [])
    
    print(f"\n🟢 Auto-Executed Actions: {len(auto_executed)}")
    for action in auto_executed:
        print(f"  - {action.get('action_name')}")
    
    print(f"\n🟠 Pending Approval Actions: {len(pending_approval)}")
    for action in pending_approval:
        print(f"  - {action.get('action_name')} (ID: {action.get('action_id')})")
    
    # Check orchestrator's pending actions list
    pending_in_orchestrator = orchestrator.get_pending_actions()
    print(f"\n📋 Orchestrator Pending Queue: {len(pending_in_orchestrator)} items")
    for action in pending_in_orchestrator:
        print(f"  - {action.get('action_name')} (ID: {action.get('action_id')})")
        print(f"    Parameters: {json.dumps(action.get('parameters', {}), indent=4)}")
    
    # Test approval if there are pending actions
    if pending_in_orchestrator:
        print("\n✅ Testing Approval Flow...")
        first_action = pending_in_orchestrator[0]
        action_id = first_action.get('action_id')
        
        print(f"  Approving: {first_action.get('action_name')} (ID: {action_id})")
        approval_result = await orchestrator.approve_action(action_id)
        
        if approval_result.get('status') == 'success':
            print("  ✅ Action approved and executed!")
            print(f"  Result: {approval_result.get('result', 'No result')[:200]}")
        else:
            print(f"  ❌ Approval failed: {approval_result.get('error', 'Unknown error')}")
    else:
        print("\n⚠️ No actions pending approval - checking if email tool was called at all")
        
        # Check if send_email_response was in the tool calls
        tool_calls = result.get('tool_calls', [])
        email_tools_called = [tc for tc in tool_calls if 'email' in tc.get('tool', '').lower()]
        
        if email_tools_called:
            print(f"  Email tools called: {len(email_tools_called)}")
            for tc in email_tools_called:
                print(f"    - {tc.get('tool')}: {tc.get('result', '')[:100]}")
        else:
            print("  ❌ No email tools were called - AI didn't attempt to send email")
            print("  💡 The AI should have called 'send_email_response' based on the explicit request")
    
    print("\n" + "="*70)
    print("✅ Test complete!")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(test_email_approval())