#!/usr/bin/env python3
"""
Test script to verify that emails are NOT sent without approval in approval mode
"""

import asyncio
import logging
from datetime import datetime

from factory_automation.factory_database.connection import get_db
from factory_automation.factory_database.models import ActionAudit
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_agents.orchestrator_with_human import OrchestratorWithHuman

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_approval_mode():
    """Test that emails require approval before sending"""
    
    print("\n" + "="*60)
    print("TESTING APPROVAL MODE - Phase 6")
    print("="*60)
    
    # Initialize orchestrator (will use approval_mode from config.yaml)
    chromadb_client = ChromaDBClient()
    orchestrator = OrchestratorWithHuman(chromadb_client, use_mock_gmail=True)
    
    print(f"\n✅ Orchestrator initialized in {'APPROVAL' if orchestrator.approval_mode else 'SDK'} mode")
    
    # Test email from standard test case
    email_data = {
        "message_id": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "from": "trimsblr@yahoo.co.in",
        "subject": "Pro-Forma Invoice #1542 for Allen Solly tags",
        "body": """Dear Sir,

Please find attached Pro-Forma Invoice #1542 for Allen Solly tags as requested.

Items included:
- AS RELAXED CROP WB tags - 500 units
- AS BOOTCUT tags - 300 units
- AS SKINNY FIT tags - 200 units

Please confirm the order and proceed with payment.

Best regards,
Interface Direct""",
        "email_type": "order",
        "attachments": []
    }
    
    print("\n📧 Processing test email...")
    print(f"   From: {email_data['from']}")
    print(f"   Subject: {email_data['subject']}")
    
    # Process the email
    result = await orchestrator.process_email(email_data)
    
    print("\n📊 Processing Result:")
    print(f"   Status: {result.get('status')}")
    print(f"   Workflow ID: {result.get('workflow_id')}")
    
    if orchestrator.approval_mode:
        # Check for pending actions
        auto_executed = result.get('auto_executed', 0)
        pending_approval = result.get('pending_approval', 0)
        
        print("\n🔄 Actions Summary:")
        print(f"   ✅ Auto-executed (reversible): {auto_executed}")
        print(f"   ⏳ Pending approval (irreversible): {pending_approval}")
        
        # Check database for pending actions
        workflow_id = result.get('workflow_id')
        if workflow_id:
            with get_db() as db:
                pending_actions = db.query(ActionAudit).filter(
                    ActionAudit.workflow_id == workflow_id,
                    ActionAudit.executed == 0,  # Use 0 for false since it's stored as integer
                    ActionAudit.action_type == 'irreversible'
                ).all()
                
                print("\n🗄️ Database Check:")
                print(f"   Found {len(pending_actions)} pending irreversible actions")
                
                for action in pending_actions:
                    print(f"   - {action.action_name} (ID: {action.action_id})")
                    if action.action_name == 'send_email_response':
                        print("   ⚠️ EMAIL ACTION FOUND - NOT EXECUTED!")
                
                # Check if any emails were actually executed
                executed_emails = db.query(ActionAudit).filter(
                    ActionAudit.workflow_id == workflow_id,
                    ActionAudit.action_name == 'send_email_response',
                    ActionAudit.executed == 1  # Use 1 for true since it's stored as integer
                ).all()
                
                if executed_emails:
                    print("\n❌ FAILURE: Found executed email actions!")
                    for email_action in executed_emails:
                        print(f"   - {email_action.action_id}: {email_action.result}")
                else:
                    print("\n✅ SUCCESS: No emails were sent without approval!")
        
        # Check the actions structure
        if 'actions' in result:
            pending = result['actions'].get('pending', [])
            executed = result['actions'].get('executed', [])
            
            print("\n📝 Action Details:")
            print(f"   Executed actions: {len(executed)}")
            for action in executed[:3]:  # Show first 3
                print(f"     - {action.get('action_name', 'unknown')}")
            
            print(f"   Pending actions: {len(pending)}")
            for action in pending:
                print(f"     - {action.get('action_name', 'unknown')} [{action.get('status')}]")
                if action.get('action_name') == 'send_email_response':
                    print(f"       Message: {action.get('message', '')}")
    else:
        print("\n⚠️ Orchestrator is in SDK mode - tools execute immediately")
        print("   To test approval mode, set 'approval_mode: true' in config.yaml")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_approval_mode())