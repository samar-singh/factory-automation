#!/usr/bin/env python3
"""Final test of AI integration."""

import asyncio
import sys

sys.path.append(".")

from factory_automation.factory_agents.ai_bridge import get_ai_bridge
from factory_automation.factory_database.vector_db import ChromaDBClient

# Test order
test_order = """Dear Interface Team,

We need urgent delivery of the following items:

1. VH cotton blue tags - 500 pieces
2. Allen Solly main tag with gold print - 300 pieces  
3. Peter England formal tag in polyester - 200 pieces
4. SYMBOL hand tag black color - 150 pieces
5. FM sustainable tags (FSC certified) - 400 pieces

This is urgent - we need delivery by next week.

Best regards,
Premium Customer"""


async def test_final():
    """Final comprehensive test."""
    try:
        print("🚀 FINAL AI INTEGRATION TEST")
        print("=" * 80)

        # Initialize
        print("\n1. Initializing AI components...")
        chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
        ai_bridge = get_ai_bridge(chroma_client=chroma_client)
        print("✅ AI components ready")

        # Process order
        print("\n2. Processing order with GPT-4...")
        df, recommendation, ai_context = await ai_bridge.process_order_with_ai(
            test_order
        )

        print("\n✅ AI PROCESSING COMPLETE!")
        print("=" * 80)

        # Results
        print(f"\n📊 RESULTS ({df.shape[0]} items processed):")
        print("-" * 80)

        for idx, row in df.iterrows():
            print(f"\n{idx + 1}. {row['Order Line']}")
            print(f"   Match: {row['Best Match']}")
            print(f"   Stock: {row['Stock Status']}")
            print(f"   Confidence: {row['Confidence']}")
            print(f"   Action: {row['Action']}")
            if row["AI Understanding"]:
                print(f"   AI Notes: {row['AI Understanding']}")

        print("\n" + "=" * 80)
        print("📝 AI RECOMMENDATION:")
        print(recommendation)

        print("\n" + "=" * 80)
        print("🧠 AI UNDERSTANDING:")
        print(ai_context["ai_understanding"][:500] + "...")

        # Summary
        print("\n" + "=" * 80)
        print("📈 SUMMARY:")
        total_items = df.shape[0]
        auto_approved = len(df[df["Action"] == "Auto-approve"])
        needs_review = len(df[df["Action"] == "Review"])
        needs_alternative = len(df[df["Action"] == "Find alternative"])
        no_match = len(df[df["Best Match"] == "No match found"])

        print(f"Total items: {total_items}")
        print(f"Auto-approved: {auto_approved} ({auto_approved/total_items*100:.1f}%)")
        print(f"Needs review: {needs_review} ({needs_review/total_items*100:.1f}%)")
        print(f"Needs alternative: {needs_alternative}")
        print(f"No matches: {no_match}")

        print("\n✅ AI SYSTEM FULLY OPERATIONAL!")

    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()


asyncio.run(test_final())
