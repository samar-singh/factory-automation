"""Test Human Interaction with detailed logging to catch the error"""

import asyncio
import json
import logging

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from factory_automation.factory_agents.orchestrator_with_human import (
    OrchestratorWithHuman
)
from factory_automation.factory_database.vector_db import ChromaDBClient


async def test_direct_tool_call():
    """Test calling the create_human_review tool directly"""
    
    print("\n" + "=" * 50)
    print("Testing Direct Tool Call")
    print("=" * 50)
    
    chromadb_client = ChromaDBClient()
    orchestrator = OrchestratorWithHuman(chromadb_client)
    
    # Find the create_human_review tool
    create_review_tool = None
    for tool in orchestrator.tools:
        if hasattr(tool, '_name') and tool._name == 'create_human_review':
            create_review_tool = tool
            break
    
    if not create_review_tool:
        print("❌ Could not find create_human_review tool")
        return
    
    print("✅ Found create_human_review tool")
    
    # Test Case 1: Empty strings (this might cause the JSON error)
    print("\nTest 1: Empty strings")
    try:
        result = await create_review_tool._func(
            email_data="",  # Empty string
            search_results="",  # Empty string
            confidence_score=70.0,
            extracted_items=""  # Empty string
        )
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error with empty strings: {e}")
    
    # Test Case 2: Valid JSON strings
    print("\nTest 2: Valid JSON strings")
    try:
        result = await create_review_tool._func(
            email_data=json.dumps({"from": "test@example.com", "subject": "Test"}),
            search_results=json.dumps([{"item": "test"}]),
            confidence_score=70.0,
            extracted_items=json.dumps([{"quantity": 100}])
        )
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error with JSON strings: {e}")
    
    # Test Case 3: Dict/List objects (shouldn't work with original code)
    print("\nTest 3: Dict/List objects")
    try:
        result = await create_review_tool._func(
            email_data={"from": "test@example.com", "subject": "Test"},
            search_results=[{"item": "test"}],
            confidence_score=70.0,
            extracted_items=[{"quantity": 100}]
        )
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error with dict/list objects: {e}")
    
    # Test Case 4: None values
    print("\nTest 4: None values")
    try:
        result = await create_review_tool._func(
            email_data=None,
            search_results=None,
            confidence_score=70.0,
            extracted_items=None
        )
        print(f"Result: {result}")
    except Exception as e:
        print(f"Error with None values: {e}")


async def test_orchestrator_scenario():
    """Test a scenario that might trigger the error in the orchestrator"""
    
    print("\n" + "=" * 50)
    print("Testing Orchestrator Scenario")
    print("=" * 50)
    
    chromadb_client = ChromaDBClient()
    orchestrator = OrchestratorWithHuman(chromadb_client)
    
    # Simulate what happens when the orchestrator processes an email
    # and the AI agent calls create_human_review
    
    test_email = {
        "message_id": "test_001",
        "from": "customer@example.com",
        "subject": "Order Request",
        "body": "Need 500 tags",
        "email_type": "order"
    }
    
    # This is what the orchestrator might do internally
    print("\nSimulating orchestrator internal flow...")
    
    # The AI agent might generate empty or malformed strings
    # when calling the tool, which could cause the JSON parsing error
    
    # Simulate various AI agent outputs
    test_cases = [
        ("Empty response", "", "", ""),
        ("Whitespace only", "  ", "  ", "  "),
        ("Invalid JSON", "{invalid", "[invalid", "{invalid"),
        ("Mixed types", "{}", "[]", "null"),
    ]
    
    for name, email_str, results_str, items_str in test_cases:
        print(f"\nTest: {name}")
        print(f"  email_data: '{email_str}'")
        print(f"  search_results: '{results_str}'")
        print(f"  extracted_items: '{items_str}'")
        
        # Find and call the tool
        for tool in orchestrator.tools:
            if hasattr(tool, '_name') and tool._name == 'create_human_review':
                try:
                    result = await tool._func(
                        email_data=email_str,
                        search_results=results_str,
                        confidence_score=70.0,
                        extracted_items=items_str
                    )
                    if "Error" in result:
                        print(f"  ❌ {result}")
                    else:
                        print(f"  ✅ {result}")
                except Exception as e:
                    print(f"  ❌ Exception: {e}")
                break


async def main():
    """Run all tests"""
    
    print("\n🔍 Testing Human Interaction Error Scenarios\n")
    
    await test_direct_tool_call()
    await test_orchestrator_scenario()
    
    print("\n✅ All tests complete!")


if __name__ == "__main__":
    asyncio.run(main())