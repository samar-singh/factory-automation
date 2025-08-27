#!/usr/bin/env python3
"""
Test Phase 3 - Action tracking in orchestrator
Verifies that actions are tracked in the audit log

Usage with uv:
    uv run python test_phase3_tracking.py
"""

import asyncio
from datetime import datetime

from factory_automation.factory_agents.orchestrator_v3_agentic import AgenticOrchestratorV3
from factory_automation.factory_database.connection import get_db
from factory_automation.factory_database.models import ActionAudit
from factory_automation.factory_database.vector_db import ChromaDBClient


async def test_action_tracking():
    """Test that orchestrator tracks actions in audit log"""
    
    print("🧪 Testing Phase 3 - Action Tracking...")
    
    # Initialize orchestrator
    chromadb_client = ChromaDBClient()
    orchestrator = AgenticOrchestratorV3(chromadb_client, use_mock_gmail=False)
    
    # Create a test email
    test_email = {
        "message_id": "test-123",
        "from": "customer@test.com",
        "to": "orders@factory.com",
        "subject": "Test Order for Allen Solly Tags",
        "body": "Please provide a quote for 500 Allen Solly tags.",
        "attachments": [],
        "timestamp": datetime.now().isoformat()
    }
    
    print("\n📧 Processing test email...")
    print(f"  From: {test_email['from']}")
    print(f"  Subject: {test_email['subject']}")
    
    # Process the email
    result = await orchestrator.process_email(test_email)
    
    # Check results
    print("\n📊 Processing Results:")
    print(f"  Success: {result.get('success')}")
    print(f"  Workflow ID: {result.get('workflow_id')}")
    print(f"  Actions Tracked: {result.get('actions_tracked', 0)}")
    print(f"  Tool Calls: {len(result.get('tool_calls', []))}")
    
    # Check the database for tracked actions
    workflow_id = result.get('workflow_id')
    if workflow_id:
        print(f"\n🔍 Checking audit log for workflow {workflow_id}...")
        
        with get_db() as db:
            # Query actions for this workflow
            actions = db.query(ActionAudit).filter_by(workflow_id=workflow_id).all()
            
            print(f"  Found {len(actions)} actions in audit log")
            
            for action in actions[:5]:  # Show first 5 actions
                print(f"\n  📝 Action: {action.action_name}")
                print(f"     ID: {action.action_id}")
                print(f"     Type: {action.action_type}")
                print(f"     Category: {action.action_category}")
                print(f"     Executed: {'Yes' if action.executed else 'No'}")
                print(f"     Requires Approval: {'Yes' if action.requires_approval else 'No'}")
                print(f"     Can Rollback: {'Yes' if action.can_rollback else 'No'}")
            
            # Clean up test data
            print("\n🧹 Cleaning up test data...")
            for action in actions:
                db.delete(action)
            db.commit()
            print("  ✅ Test data cleaned")
    
    # Display reasoning if available
    if result.get('reasoning'):
        print("\n💭 Reasoning Generated:")
        print(result['reasoning'][:500])
    
    print("\n✅ Phase 3 Action Tracking Test Complete!")
    return True


if __name__ == "__main__":
    try:
        asyncio.run(test_action_tracking())
    except Exception as e:
        print(f"\n❌ Error testing action tracking: {e}")
        import traceback
        traceback.print_exc()
        exit(1)