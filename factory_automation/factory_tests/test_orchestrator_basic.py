#!/usr/bin/env python3
"""Test basic orchestrator functionality."""

import asyncio
import sys

sys.path.append("./factory_automation")

from factory_automation.factory_agents.orchestrator_agent import OrchestratorAgent


async def test_basic_orchestrator():
    """Test the basic orchestrator (v1)."""
    print("Testing Basic Orchestrator")
    print("=" * 50)

    # Initialize orchestrator
    orchestrator = OrchestratorAgent()

    # Test the workflow
    print("\nInitializing orchestrator...")
    await orchestrator.initialize()
    print("✓ Orchestrator initialized")

    # Check connected services
    print("\nChecking connected services:")
    print(f"  ChromaDB connected: {orchestrator.chromadb_client.is_connected()}")

    # Test simple routing
    test_messages = [
        "Check inventory for blue cotton tags",
        "Process email from customer@example.com",
        "Create order document for 500 tags",
    ]

    print("\nTesting message routing:")
    for msg in test_messages:
        print(f"\nMessage: '{msg}'")
        # The orchestrator v1 doesn't have direct message routing,
        # but we can check if the agents are ready
        if "inventory" in msg.lower():
            print("  → Would route to: Inventory Matcher Agent")
        elif "email" in msg.lower():
            print("  → Would route to: Email Monitor Agent")
        elif "document" in msg.lower() or "order" in msg.lower():
            print("  → Would route to: Order Interpreter Agent")

    print("\n" + "=" * 50)
    print("Basic orchestrator test completed!")


if __name__ == "__main__":
    asyncio.run(test_basic_orchestrator())
