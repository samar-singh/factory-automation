#!/usr/bin/env python3
"""Debug AI integration with pdb."""

import asyncio
import pdb
import sys

sys.path.append(".")

from factory_automation.factory_agents.ai_bridge_debug import get_ai_bridge_debug
from factory_automation.factory_database.vector_db import ChromaDBClient

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


async def debug_ai_processing():
    """Debug the AI processing of orders with pdb."""
    print("Starting debug session...")
    print("Commands: n (next), s (step into), c (continue), l (list), p <var> (print)")
    print("-" * 80)

    try:
        # Initialize components
        print("Initializing AI components...")
        chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
        ai_bridge = get_ai_bridge_debug(chroma_client=chroma_client)
        print("✅ AI components initialized")

        # Set breakpoint before AI processing
        print("\n🔴 Setting breakpoint before AI order processing...")
        pdb.set_trace()

        # Process the order - we can step through this
        df, recommendation, ai_context = await ai_bridge.process_order_with_ai(
            test_order
        )

        print("\n✅ AI Processing Complete!")
        print(f"Results shape: {df.shape}")
        print(f"Recommendation length: {len(recommendation)}")
        print(f"AI context keys: {list(ai_context.keys())}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n🔴 Entering post-mortem debugging...")
        pdb.post_mortem()


def main():
    """Run the async debug function."""
    print("=" * 80)
    print("PDB DEBUGGING SESSION - AI INTEGRATION")
    print("=" * 80)

    # Run the async function
    asyncio.run(debug_ai_processing())

    print("\n" + "=" * 80)
    print("DEBUG SESSION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    main()
