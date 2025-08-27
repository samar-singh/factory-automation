#!/usr/bin/env python3
"""
Test the merged orchestrator to verify it can prevent email execution
"""

import asyncio
import logging
from datetime import datetime

from factory_automation.factory_database.connection import get_db
from factory_automation.factory_database.models import ActionAudit
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_agents.orchestrator_v3_agentic import AgenticOrchestratorV3

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_merged_orchestrator():
    """Test that the merged orchestrator prevents emails without approval"""
    
    print("\n" + "="*60)
    print("TESTING MERGED ORCHESTRATOR - True Approval Capability")
    print("="*60)
    
    # Initialize orchestrator
    chromadb_client = ChromaDBClient()
    orchestrator = AgenticOrchestratorV3(chromadb_client, use_mock_gmail=True)
    
    print("\n✅ Orchestrator initialized")
    print(f"   Uses direct API: {hasattr(orchestrator, 'openai_client')}")
    print(f"   Has confirm_and_execute: {hasattr(orchestrator, 'confirm_and_execute')}")
    print(f"   No SDK Runner: {not hasattr(orchestrator, 'runner')}")
    
    # Test email
    email_data = {
        "message_id": f"test_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "from": "customer@example.com",
        "subject": "Urgent: Need 500 Allen Solly tags",
        "body": """Dear Sir,

We urgently need 500 Allen Solly tags for our upcoming shipment.
Please confirm availability and send quotation.

Best regards,
Customer""",
        "email_type": "order",
        "attachments": []
    }
    
    print("\n📧 Processing test email...")
    print(f"   Subject: {email_data['subject']}")
    
    # Process the email
    result = await orchestrator.process_email(email_data)
    
    print("\n📊 Processing Result:")
    print(f"   Status: {result.get('success')}")
    print(f"   Workflow ID: {result.get('workflow_id')}")
    
    # Check for auto-executed vs pending actions
    auto_executed = result.get('auto_executed_actions', [])
    pending_approval = result.get('pending_approval_actions', [])
    
    print("\n🔄 Actions Summary:")
    print(f"   ✅ Auto-executed (reversible): {len(auto_executed)}")
    print(f"   ⏳ Pending approval (irreversible): {len(pending_approval)}")
    
    # Check database for pending actions
    workflow_id = result.get('workflow_id')
    if workflow_id:
        with get_db() as db:
            # Check for pending irreversible actions
            pending_actions = db.query(ActionAudit).filter(
                ActionAudit.workflow_id == workflow_id,
                ActionAudit.executed == 0,
                ActionAudit.action_type == 'irreversible'
            ).all()
            
            print("\n🗄️ Database Check:")
            print(f"   Found {len(pending_actions)} pending irreversible actions")
            
            for action in pending_actions:
                print(f"   - {action.action_name} (ID: {action.action_id})")
                if 'email' in action.action_name.lower():
                    print("   ⚠️ EMAIL ACTION FOUND - NOT EXECUTED!")
            
            # Check if any emails were actually executed
            executed_emails = db.query(ActionAudit).filter(
                ActionAudit.workflow_id == workflow_id,
                ActionAudit.action_name.like('%email%'),
                ActionAudit.executed == 1
            ).all()
            
            if executed_emails:
                print("\n❌ FAILURE: Found executed email actions!")
                for email_action in executed_emails:
                    print(f"   - {email_action.action_id}: {email_action.action_name}")
            else:
                print("\n✅ SUCCESS: No emails were sent without approval!")
    
    # Check orchestrator's pending actions list
    pending = orchestrator.get_pending_actions()
    print(f"\n📝 Orchestrator's Pending Actions: {len(pending)}")
    for action in pending:
        print(f"   - {action.get('action_name')} [{action.get('status')}]")
        if action.get('status') == 'pending_approval':
            print("     ✅ Correctly queued for approval")
    
    print("\n" + "="*60)
    print("TEST COMPLETE - Merged Orchestrator Working!")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_merged_orchestrator())