#!/usr/bin/env python3
"""
Integration test using standard test case
Run this after each phase to verify implementation

Usage with uv:
    uv run python test_phase_integration.py
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from factory_automation.factory_tests.standard_test_case import (
    get_test_email,
    assert_phase_3_behavior,
    assert_phase_4_behavior
)
from factory_automation.factory_agents.orchestrator_v3_agentic import AgenticOrchestratorV3
from factory_automation.factory_database.connection import get_db
from factory_automation.factory_database.models import ActionAudit
from factory_automation.factory_database.vector_db import ChromaDBClient


async def test_current_implementation():
    """Test the current implementation with standard test case"""
    
    print("=" * 70)
    print("🧪 INTEGRATION TEST - STANDARD TEST CASE")
    print("=" * 70)
    
    # Get test data
    test_email = get_test_email()
    
    print("\n📧 Test Email:")
    print(f"  From: {test_email['from']}")
    print(f"  To: {test_email['to']}")
    print(f"  Subject: {test_email['subject']}")
    print(f"  Attachments: {len(test_email.get('attachments', []))} file(s)")
    
    # Initialize orchestrator
    print("\n🚀 Initializing orchestrator...")
    chromadb_client = ChromaDBClient()
    orchestrator = AgenticOrchestratorV3(chromadb_client, use_mock_gmail=False)
    
    # Process the email
    print("\n⚙️ Processing email...")
    try:
        result = await orchestrator.process_email(test_email)
        
        print("\n📊 Processing Results:")
        print(f"  ✓ Success: {result.get('success')}")
        print(f"  ✓ Workflow ID: {result.get('workflow_id')}")
        print(f"  ✓ Actions Tracked: {result.get('actions_tracked', 0)}")
        print(f"  ✓ Tool Calls: {len(result.get('tool_calls', []))}")
        
        # Check action tracking in database
        workflow_id = result.get('workflow_id')
        if workflow_id:
            print(f"\n🔍 Checking audit log for workflow {workflow_id}...")
            
            with get_db() as db:
                actions = db.query(ActionAudit).filter_by(workflow_id=workflow_id).all()
                
                print(f"  Found {len(actions)} actions in audit log")
                
                # Analyze action types
                reversible_count = 0
                irreversible_count = 0
                
                print("\n📝 Action Classification:")
                for action in actions:
                    if action.action_type == 'reversible':
                        reversible_count += 1
                        icon = "🟢"
                    else:
                        irreversible_count += 1
                        icon = "🟠"
                    
                    print(f"  {icon} {action.action_name:30} -> {action.action_type:12} ({action.action_category})")
                
                print("\n📊 Summary:")
                print(f"  Reversible actions: {reversible_count}")
                print(f"  Irreversible actions: {irreversible_count}")
                
                # Phase 3 validation
                print("\n✅ Phase 3 Validation:")
                phase_3_errors = assert_phase_3_behavior(result)
                if phase_3_errors:
                    for error in phase_3_errors:
                        print(f"  ❌ {error}")
                else:
                    print("  ✓ All Phase 3 requirements met")
                
                # Check if Phase 4 is implemented
                if result.get('auto_executed_actions') or result.get('pending_approval_actions'):
                    print("\n✅ Phase 4 Validation:")
                    phase_4_errors = assert_phase_4_behavior(result)
                    if phase_4_errors:
                        for error in phase_4_errors:
                            print(f"  ❌ {error}")
                    else:
                        print("  ✓ All Phase 4 requirements met")
                
                # Clean up test data
                print("\n🧹 Cleaning up test data...")
                for action in actions:
                    db.delete(action)
                db.commit()
                print("  ✓ Test data cleaned")
        
    except Exception as e:
        print(f"\n❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()
        
        # Check if it's API key issue
        if "OPENAI_API_KEY" in str(e):
            print("\n⚠️ Note: OPENAI_API_KEY not set. Testing without agent execution.")
            print("  Action tracking mechanisms are in place but won't generate actions without the agent.")
            
            # Test the tracking mechanism directly
            print("\n🔧 Testing action tracking mechanism directly...")
            
            # Generate workflow ID
            orchestrator.current_workflow_id = orchestrator._generate_workflow_id()
            print(f"  Workflow ID: {orchestrator.current_workflow_id}")
            
            # Track a sample action
            action_id = await orchestrator._track_action(
                action_name="send_email_response",
                action_category="customer_communication",
                details={"to": test_email['from'], "subject": "Re: " + test_email['subject']},
                confidence=0.75,
                order_id=None
            )
            
            print(f"  Action ID: {action_id}")
            
            # Verify in database
            with get_db() as db:
                action = db.query(ActionAudit).filter_by(action_id=action_id).first()
                
                if action:
                    print("\n  ✓ Action tracked successfully:")
                    print(f"    - Name: {action.action_name}")
                    print(f"    - Type: {action.action_type}")
                    print(f"    - Requires Approval: {action.requires_approval}")
                    
                    # Clean up
                    db.delete(action)
                    db.commit()
    
    print("\n" + "=" * 70)
    print("✅ Integration test complete!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_current_implementation())