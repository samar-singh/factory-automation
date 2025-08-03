#!/usr/bin/env python3
"""Test the AI-integrated Gradio app."""

import asyncio
import sys

sys.path.append(".")

from factory_automation.factory_agents.ai_bridge import get_ai_bridge
from factory_automation.factory_database.vector_db import ChromaDBClient

print("=" * 80)
print("TESTING AI INTEGRATION")
print("=" * 80)

# Test order
test_order = """Dear Interface Team,

Please find our order for the following items:
1. VH cotton blue tags - 500 pieces
2. Allen Solly main tag with gold print - 300 pieces
3. Peter England formal tag in polyester - 200 pieces
4. SYMBOL hand tag black color - 150 pieces

This is urgent - we need delivery by next week.

Best regards,
Test Customer"""


async def test_ai_processing():
    """Test the AI processing of orders."""
    try:
        # Initialize components
        print("\n1. Initializing AI components...")
        chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
        ai_bridge = get_ai_bridge(chroma_client=chroma_client)
        print("✅ AI components initialized")

        # Test AI order processing
        print("\n2. Testing AI order processing...")
        print("-" * 50)
        print("Order Text:")
        print(test_order)
        print("-" * 50)

        # Process the order
        df, recommendation, ai_context = await ai_bridge.process_order_with_ai(
            test_order
        )

        print("\n✅ AI Processing Complete!")
        print("\nResults DataFrame:")
        print(df)
        print("\nAI Recommendation:")
        print(recommendation)
        print("\nAI Context Keys:")
        print(list(ai_context.keys()))

        # Test AI search enhancement
        print("\n3. Testing AI-enhanced search...")
        test_query = "I need sustainable black tags for Myntra brand"
        search_df = await ai_bridge.search_with_ai_enhancement(
            test_query, confidence_threshold=50, max_results=5
        )
        print(f"\nSearch for: '{test_query}'")
        print(search_df)

        # Test orchestrator directly
        print("\n4. Testing orchestrator directly...")
        test_result = await ai_bridge.orchestrator.handle_complex_request(
            "What inventory matching capabilities do you have?", context={"test": True}
        )
        print(f"Orchestrator test: {test_result.get('success')}")
        if test_result.get("success"):
            print(f"Response: {test_result.get('result')[:200]}...")

    except Exception as e:
        print(f"❌ Error in AI testing: {e}")
        import traceback

        traceback.print_exc()


# Run the async test
print("\nStarting AI integration test...")
asyncio.run(test_ai_processing())

print("\n" + "=" * 80)
print("AI INTEGRATION TEST COMPLETE")
print("=" * 80)
