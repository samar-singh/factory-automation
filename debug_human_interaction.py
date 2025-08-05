"""Debug script for Human Interaction System parsing error"""

import asyncio
import json

from factory_automation.factory_agents.orchestrator_with_human import (
    OrchestratorWithHuman
)
from factory_automation.factory_database.vector_db import ChromaDBClient


async def debug_parsing_error():
    """Debug the JSON parsing error in create_human_review"""
    
    print("=" * 50)
    print("Debugging JSON Parsing Error")
    print("=" * 50)
    
    # Initialize components
    chromadb_client = ChromaDBClient()
    orchestrator = OrchestratorWithHuman(chromadb_client)
    
    # Test data that might be causing the error
    test_email = {
        "message_id": "test_msg_001",
        "from": "test@example.com",
        "subject": "Test Order",
        "body": "Test body",
        "email_type": "order"
    }
    
    test_search_results = [
        {
            "item_id": "TAG001",
            "name": "Test Tag",
            "similarity_score": 0.65
        }
    ]
    
    test_items = [
        {
            "quantity": 100,
            "description": "test tags"
        }
    ]
    
    print("\n1. Testing with dict objects directly...")
    
    # Try calling the function directly (this might be what's happening)
    try:
        # Get the create_human_review function from tools
        create_review_func = None
        for tool in orchestrator.tools:
            if hasattr(tool, '_name') and tool._name == 'create_human_review':
                create_review_func = tool._func
                break
        
        if create_review_func:
            print("Found create_human_review function")
            
            # Test 1: Pass dicts directly (might cause error)
            print("\nTest 1: Passing dicts directly")
            result = await create_review_func(
                email_data=test_email,  # Dict, not JSON string
                search_results=test_search_results,  # List, not JSON string
                confidence_score=65.0,
                extracted_items=test_items  # List, not JSON string
            )
            print(f"Result: {result}")
            
    except Exception as e:
        print(f"Error with dicts: {e}")
        
        # Test 2: Pass JSON strings (should work)
        print("\nTest 2: Passing JSON strings")
        result = await create_review_func(
            email_data=json.dumps(test_email),
            search_results=json.dumps(test_search_results),
            confidence_score=65.0,
            extracted_items=json.dumps(test_items)
        )
        print(f"Result: {result}")
    
    print("\n2. Testing with human_manager directly...")
    
    # This should always work
    review = await orchestrator.human_manager.create_review_request(
        email_data=test_email,
        search_results=test_search_results,
        confidence_score=65.0,
        extracted_items=test_items
    )
    
    print(f"Direct call result: {review.request_id}")
    
    print("\n" + "=" * 50)
    print("Debug Complete")
    print("=" * 50)


async def test_orchestrator_process_email():
    """Test the full orchestrator process_email flow"""
    
    print("\n" + "=" * 50)
    print("Testing Orchestrator Process Email")
    print("=" * 50)
    
    chromadb_client = ChromaDBClient()
    orchestrator = OrchestratorWithHuman(chromadb_client)
    
    test_email = {
        "message_id": "test_msg_003",
        "from": "myntra@example.com",
        "subject": "Order for eco-friendly tags",
        "body": "Need 1000 recycled paper tags",
        "attachments": []
    }
    
    print("\nProcessing email through orchestrator...")
    print(f"Email: {test_email}")
    
    # Add debug logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Process through orchestrator
    result = await orchestrator.process_email(test_email)
    
    print(f"\nResult: {result}")
    
    if not result['success']:
        print(f"Error: {result.get('error', 'Unknown error')}")
        
        # Check if it's an API key issue
        import os
        if 'OPENAI_API_KEY' not in os.environ:
            print("\n⚠️  OPENAI_API_KEY not set in environment")
            print("This is likely why the orchestrator processing fails")


def main():
    """Run debug tests"""
    
    print("\n🔍 Starting Debug Session\n")
    
    # Run parsing debug
    asyncio.run(debug_parsing_error())
    
    # Run orchestrator test
    asyncio.run(test_orchestrator_process_email())
    
    print("\n✅ Debug session complete!")


if __name__ == "__main__":
    main()