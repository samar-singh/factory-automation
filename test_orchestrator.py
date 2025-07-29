#!/usr/bin/env python3
"""Test the AI-powered orchestrator v2."""

import asyncio
import sys
sys.path.append('./factory_automation')

from factory_automation.factory_agents.orchestrator_v2_agent import OrchestratorV2, orchestrator_agent

async def test_orchestrator():
    """Test various scenarios with the orchestrator."""
    print("Testing AI-Powered Orchestrator V2")
    print("=" * 50)
    
    # Initialize orchestrator
    orchestrator = OrchestratorV2()
    
    # Test scenarios
    test_cases = [
        {
            "name": "Order Email Processing",
            "message": "We received an email from customer@example.com with subject 'Order Request - Blue Cotton Tags'. They want 500 blue cotton tags size 2x3 inches."
        },
        {
            "name": "Inventory Search",
            "message": "Can you search our inventory for red silk tags?"
        },
        {
            "name": "Payment Processing",
            "message": "We received a payment screenshot showing UTR number 123456789 for order ORD-2024-001"
        },
        {
            "name": "Approval Request",
            "message": "Customer wants a custom purple leather tag design. Should we approve this?"
        },
        {
            "name": "Status Check",
            "message": "What's the status of order ORD-2024-002?"
        }
    ]
    
    for test in test_cases:
        print(f"\n{'='*50}")
        print(f"Test: {test['name']}")
        print(f"Message: {test['message']}")
        print("-" * 50)
        
        try:
            # Process the request
            result = await orchestrator.process_request(
                request_type="test",
                request_data={
                    "message": test["message"],
                    "context": {
                        "source": "test_script",
                        "timestamp": "2024-01-29T10:00:00"
                    }
                }
            )
            
            print("Result:")
            print(f"  Status: {result.get('status', 'unknown')}")
            print(f"  Action: {result.get('action', 'none')}")
            print(f"  Agent: {result.get('agent', 'none')}")
            if 'reasoning' in result:
                print(f"  Reasoning: {result['reasoning']}")
            if 'data' in result:
                print(f"  Data: {result['data']}")
            
        except Exception as e:
            print(f"Error: {str(e)}")
    
    print("\n" + "="*50)
    print("Orchestrator test completed!")

if __name__ == "__main__":
    asyncio.run(test_orchestrator())