#!/usr/bin/env python3
"""Test system after tool cleanup"""

import asyncio

from factory_automation.factory_agents.orchestrator_with_human import (
    OrchestratorWithHuman,
)
from factory_automation.factory_database.vector_db import ChromaDBClient


async def test_cleanup():
    print("=" * 60)
    print("TESTING SYSTEM AFTER TOOL CLEANUP")
    print("=" * 60)

    # Initialize
    chromadb_client = ChromaDBClient()
    orchestrator = OrchestratorWithHuman(chromadb_client)

    # Get tools
    tools = orchestrator._create_tools()
    tool_names = [t.__name__ for t in tools if hasattr(t, "__name__")]

    print(f"\n✅ System initialized with {len(tools)} tools:")
    for i, name in enumerate(tool_names, 1):
        print(f"   {i}. {name}")

    # Check removed tools
    print("\n🗑️ Removed redundant tools:")
    removed = ["analyze_email", "extract_order_items", "make_decision"]
    for tool in removed:
        if tool in tool_names:
            print(f"   ❌ {tool} still exists (should be removed)")
        else:
            print(f"   ✅ {tool} successfully removed")

    # Check essential tools
    print("\n✨ Essential tools present:")
    essential = [
        "process_complete_order",
        "check_emails",
        "process_tag_image",
        "search_inventory",
    ]
    for tool in essential:
        if tool in tool_names:
            print(f"   ✅ {tool}")
        else:
            print(f"   ❌ {tool} missing!")

    # Test process_complete_order
    print("\n🧪 Testing process_complete_order tool...")
    process_order = None
    for tool in tools:
        if hasattr(tool, "__name__") and tool.__name__ == "process_complete_order":
            process_order = tool
            break

    if process_order:
        try:
            # Test with sample order
            result = await process_order(
                email_subject="Test Order - Allen Solly Tags",
                email_body="Need 1000 price tags for Allen Solly. Urgent delivery required.",
                sender_email="test@example.com",
            )
            print("   ✅ process_complete_order works!")

            import json

            result_data = json.loads(result)
            print(f"   • Order ID: {result_data.get('order_id', 'N/A')}")
            print(f"   • Action: {result_data.get('recommended_action', 'N/A')}")
            print(f"   • Confidence: {result_data.get('extraction_confidence', 0):.1%}")
        except Exception as e:
            print(f"   ❌ Error testing process_complete_order: {e}")
    else:
        print("   ❌ process_complete_order tool not found")

    print("\n" + "=" * 60)
    print("CLEANUP TEST COMPLETE")
    print("=" * 60)

    return True


if __name__ == "__main__":
    asyncio.run(test_cleanup())
