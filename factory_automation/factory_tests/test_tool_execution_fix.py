#!/usr/bin/env python3
"""
Test that the simplified tool execution works correctly
"""

import asyncio
import json
from datetime import datetime

from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_agents.orchestrator_v3_agentic import AgenticOrchestratorV3
from factory_automation.factory_tests.standard_test_case import get_test_email

async def test_tool_execution():
    """Test that tools can be executed after the fix"""
    
    print("\n" + "="*60)
    print("TESTING TOOL EXECUTION FIX")
    print("="*60)
    
    # Initialize orchestrator
    chromadb_client = ChromaDBClient()
    orchestrator = AgenticOrchestratorV3(chromadb_client, use_mock_gmail=True)
    
    print(f"\n✅ Orchestrator initialized with {len(orchestrator.tools)} tools")
    
    # Test direct tool calling from tool_map
    print("\n1️⃣ Testing direct tool execution from tool_map...")
    
    # Test with a simple tool that should be reversible
    if 'search_inventory' in orchestrator.tool_map:
        tool = orchestrator.tool_map['search_inventory']
        print(f"   Tool type: {type(tool)}")
        print(f"   Tool name: {tool.name if hasattr(tool, 'name') else 'N/A'}")
        
        try:
            # Try to call the tool directly with test parameters
            test_args = {
                "query": "Allen Solly tags",
                "max_results": 5,
                "confidence_threshold": 0.7
            }
            print(f"   Calling tool with args: {test_args}")
            result = await tool(**test_args)
            print("   ✅ Tool executed successfully!")
            print(f"   Result type: {type(result)}")
            if isinstance(result, str):
                try:
                    result_dict = json.loads(result)
                    print(f"   Found {result_dict.get('count', 0)} matches")
                except:
                    print(f"   Result: {result[:200]}...")
        except Exception as e:
            print(f"   ❌ Error executing tool: {e}")
    else:
        print("   ❌ search_inventory not found in tool_map")
    
    # Test the complete flow with email processing
    print("\n2️⃣ Testing complete email processing flow...")
    
    email_data = get_test_email()
    email_data["message_id"] = f"test_fix_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    print(f"   Processing email: {email_data['subject']}")
    
    try:
        result = await orchestrator.process_email(email_data)
        
        print("\n   ✅ Email processed successfully!")
        print(f"   Workflow ID: {result.get('workflow_id')}")
        print(f"   Success: {result.get('success')}")
        print(f"   Auto-executed: {len(result.get('auto_executed_actions', []))} actions")
        print(f"   Pending approval: {len(result.get('pending_approval_actions', []))} actions")
        
        # Show which actions were executed
        if result.get('auto_executed_actions'):
            print("\n   Auto-executed actions:")
            for action in result['auto_executed_actions']:
                print(f"      - {action.get('action_name', 'Unknown')}")
        
        # Show which actions are pending
        if result.get('pending_approval_actions'):
            print("\n   Pending approval actions:")
            for action in result['pending_approval_actions']:
                print(f"      - {action.get('action_name', 'Unknown')}")
        
    except Exception as e:
        print(f"   ❌ Error processing email: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_tool_execution())