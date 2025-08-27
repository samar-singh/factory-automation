#!/usr/bin/env python3
"""
Test that wrapped tools work properly with ToolContext
"""

import asyncio
from datetime import datetime

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_agents.orchestrator_v3_agentic import AgenticOrchestratorV3
from factory_automation.factory_tests.standard_test_case import get_test_email

async def test_wrapped_tool_execution():
    """Test that wrapped tools execute properly"""
    
    print("\n" + "="*60)
    print("TESTING WRAPPED TOOL EXECUTION WITH TOOLCONTEXT")
    print("="*60)
    
    # Initialize orchestrator
    chromadb_client = ChromaDBClient()
    orchestrator = AgenticOrchestratorV3(chromadb_client, use_mock_gmail=True)
    
    print(f"\n✅ Orchestrator initialized with {len(orchestrator.tools)} wrapped tools")
    
    # Check if tools are wrapped
    print("\n1️⃣ Checking if tools are wrapped...")
    if orchestrator.tools:
        first_tool = orchestrator.tools[0]
        print(f"   First tool name: {getattr(first_tool, 'name', 'N/A')}")
        print(f"   Is wrapped? {getattr(first_tool, 'is_wrapped', False)}")
        print(f"   Has original_tool? {hasattr(first_tool, 'original_tool')}")
    
    # Test email processing with wrapped tools
    print("\n2️⃣ Testing email processing with wrapped tools...")
    
    email_data = get_test_email()
    email_data["message_id"] = f"wrapped_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print(f"   Processing email: {email_data['subject'][:50]}...")
    
    try:
        result = await orchestrator.process_email(email_data)
        
        print("\n   ✅ Email processed successfully!")
        print(f"   Workflow ID: {result.get('workflow_id')}")
        print(f"   Success: {result.get('success')}")
        
        # Check auto-executed actions
        auto_executed = result.get('auto_executed_actions', [])
        print(f"\n   Auto-executed actions: {len(auto_executed)}")
        for action in auto_executed[:3]:  # Show first 3
            print(f"      - {action.get('action_name', 'Unknown')}")
        
        # Check pending approval actions
        pending = result.get('pending_approval_actions', [])
        print(f"\n   Pending approval actions: {len(pending)}")
        for action in pending[:3]:  # Show first 3
            print(f"      - {action.get('action_name', 'Unknown')} (ID: {action.get('action_id', 'N/A')})")
        
        # Test approval if there are pending actions
        if pending and orchestrator.pending_actions:
            print("\n3️⃣ Testing approval flow...")
            
            first_pending = orchestrator.pending_actions[0]
            action_id = first_pending.get('action_id')
            action_name = first_pending.get('action_name')
            
            print(f"   Approving action: {action_name} (ID: {action_id})")
            
            approval_result = await orchestrator.approve_action(action_id)
            
            if approval_result.get('status') == 'success':
                print("   ✅ Action approved and executed successfully!")
            else:
                print(f"   ❌ Approval failed: {approval_result.get('error', 'Unknown error')}")
        
    except Exception as e:
        print(f"   ❌ Error processing email: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_wrapped_tool_execution())