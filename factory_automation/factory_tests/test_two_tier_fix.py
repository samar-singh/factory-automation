#!/usr/bin/env python3
"""
Test script to verify two-tier execution tracking is working
with the Allen Solly standard test case.
"""

import asyncio
import json
from factory_automation.factory_agents.orchestrator_v3_agentic import AgenticOrchestratorV3
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_tests.standard_test_case import TEST_EMAIL

async def test_two_tier_tracking():
    """Test that the orchestrator properly tracks tool calls in two-tier categories"""
    print("=== Testing Two-Tier Execution Tracking ===\n")
    
    # Initialize orchestrator
    chromadb = ChromaDBClient()
    orchestrator = AgenticOrchestratorV3(chromadb, use_mock_gmail=True)
    
    # Process the standard test email
    print(f"Processing email: {TEST_EMAIL['subject']}\n")
    result = await orchestrator.process_email(TEST_EMAIL)
    
    # Display results
    print("=== Processing Results ===")
    print(f"✅ Success: {result.get('success', False)}")
    print(f"📧 Email ID: {result.get('email_id', 'unknown')}")
    print(f"🔄 Workflow ID: {result.get('workflow_id', 'unknown')}")
    print(f"🛠️  Total tool calls: {len(result.get('tool_calls', []))}")
    print(f"📊 Actions tracked in DB: {result.get('actions_tracked', 0)}")
    
    # Display tool calls with classification
    print("\n=== Tool Calls Made ===")
    for tc in result.get('tool_calls', []):
        action_type = tc.get('action_type', 'unknown')
        icon = "✅" if action_type == "reversible" else "⚠️"
        print(f"{icon} {tc['tool']:30} ({action_type:12}) - ID: {tc.get('action_id', 'N/A')}")
    
    # Display two-tier execution summary
    print("\n=== Two-Tier Execution Summary ===")
    
    auto_executed = result.get('auto_executed_actions', [])
    print(f"\n✅ Auto-Executed (Reversible): {len(auto_executed)}")
    for action in auto_executed:
        print(f"   - {action['action_name']:30} [{action['status']}]")
    
    pending_approval = result.get('pending_approval_actions', [])
    print(f"\n⚠️  Pending Approval (Irreversible): {len(pending_approval)}")
    for action in pending_approval:
        print(f"   - {action['action_name']:30} [{action['status']}]")
        if 'warning' in action:
            print(f"     ⚠️  {action['warning']}")
    
    # Check database for action audit records
    from factory_automation.factory_database.connection import get_db
    from factory_automation.factory_database.models import ActionAudit
    
    print("\n=== Database Audit Records ===")
    with get_db() as db:
        workflow_actions = db.query(ActionAudit).filter_by(
            workflow_id=result.get('workflow_id')
        ).all()
        
        print(f"Found {len(workflow_actions)} actions in database for this workflow:")
        for action in workflow_actions:
            icon = "✅" if action.action_type == "reversible" else "⚠️"
            approval = "Required" if action.requires_approval else "Not Required"
            print(f"{icon} {action.action_name:30} - Approval: {approval}, Executed: {action.executed}")
    
    # Summary
    print("\n=== Summary ===")
    if len(auto_executed) > 0 or len(pending_approval) > 0:
        print("✅ Two-tier tracking is working!")
        print(f"   - {len(auto_executed)} reversible actions would auto-execute")
        print(f"   - {len(pending_approval)} irreversible actions would require approval")
    else:
        print("❌ Two-tier tracking not working - no actions categorized")
    
    return result

if __name__ == "__main__":
    result = asyncio.run(test_two_tier_tracking())
    
    # Save result for inspection
    with open("two_tier_test_result.json", "w") as f:
        # Filter out non-serializable items
        clean_result = {
            k: v for k, v in result.items() 
            if k not in ['final_summary']
        }
        json.dump(clean_result, f, indent=2)
        print("\n💾 Full results saved to two_tier_test_result.json")