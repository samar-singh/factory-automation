#!/usr/bin/env python3
"""Simple test to identify AI integration issues."""

import asyncio
import sys
import traceback

sys.path.append(".")

from factory_automation.factory_agents.ai_bridge_debug import get_ai_bridge_debug
from factory_automation.factory_database.vector_db import ChromaDBClient

# Test order
test_order = """Dear Interface Team,

Please find our order for the following items:
1. VH cotton blue tags - 500 pieces

Best regards,
Test Customer"""


async def test_ai_simple():
    """Simple test of AI processing."""
    try:
        print("1. Initializing components...")
        chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
        ai_bridge = get_ai_bridge_debug(chroma_client=chroma_client)
        print("✅ Components initialized")

        print("\n2. Testing AI order processing...")
        print(f"Order: {test_order}")

        # Try to process
        df, recommendation, ai_context = await ai_bridge.process_order_with_ai(
            test_order
        )

        print("\n✅ Success!")
        print(f"DataFrame shape: {df.shape}")
        print(f"DataFrame:\n{df}")
        print(f"\nRecommendation:\n{recommendation}")

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        traceback.print_exc()

        # Try to understand the error
        print("\n--- Error Analysis ---")
        if "gpt-4" in str(e).lower():
            print("Issue: GPT-4 model access problem")
            print("Solution: Check OpenAI API key and model access")
        elif "openai" in str(e).lower():
            print("Issue: OpenAI API problem")
            print("Solution: Verify API key in .env file")
        else:
            print("Issue: Unknown error")


print("=" * 80)
print("SIMPLE AI TEST")
print("=" * 80)

asyncio.run(test_ai_simple())
