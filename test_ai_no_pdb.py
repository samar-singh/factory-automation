#!/usr/bin/env python3
"""Test AI integration without pdb interference."""

import asyncio
import sys
import traceback

sys.path.append(".")

from factory_automation.factory_agents.ai_bridge import get_ai_bridge
from factory_automation.factory_database.vector_db import ChromaDBClient

# Test order
test_order = """Dear Interface Team,

Please find our order for the following items:
1. VH cotton blue tags - 500 pieces
2. Allen Solly main tag with gold print - 300 pieces

Best regards,
Test Customer"""


async def test_ai_no_pdb():
    """Test AI processing without pdb."""
    try:
        print("1. Initializing components...")
        chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
        ai_bridge = get_ai_bridge(chroma_client=chroma_client)
        print("✅ Components initialized")

        print("\n2. Testing GPT-4 connection...")
        # Test GPT-4 directly
        test_understanding = await ai_bridge._analyze_order_with_gpt4(
            "Test order: 100 blue tags"
        )
        print(f"✅ GPT-4 working! Response: {test_understanding[:100]}...")

        print("\n3. Testing order line extraction...")
        order_lines = await ai_bridge._extract_order_lines_with_ai(
            test_order, test_understanding
        )
        print(f"✅ Extracted {len(order_lines)} lines")
        for i, line in enumerate(order_lines):
            print(f"  Line {i+1}: {line['query']} (qty: {line['quantity']})")

        print("\n4. Testing full AI order processing...")
        df, recommendation, ai_context = await ai_bridge.process_order_with_ai(
            test_order
        )

        print("\n✅ Full processing complete!")
        print(f"\nDataFrame shape: {df.shape}")
        print(f"\nDataFrame:\n{df}")
        print(f"\nRecommendation:\n{recommendation[:200]}...")
        print(f"\nAI Context keys: {list(ai_context.keys())}")

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        traceback.print_exc()

        # Check common issues
        print("\n--- Troubleshooting ---")
        if "api_key" in str(e).lower():
            print("Issue: OpenAI API key problem")
            print("Check: Is OPENAI_API_KEY set in .env?")
        elif "model" in str(e).lower() and "gpt-4" in str(e).lower():
            print("Issue: GPT-4 access problem")
            print("Check: Does your API key have GPT-4 access?")
            print("Try: Change to gpt-3.5-turbo in ai_bridge.py")
        elif "connection" in str(e).lower():
            print("Issue: Network/connection problem")
            print("Check: Internet connection and OpenAI API status")


print("=" * 80)
print("AI INTEGRATION TEST (No PDB)")
print("=" * 80)

asyncio.run(test_ai_no_pdb())
