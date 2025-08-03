#!/usr/bin/env python3
"""Test the fixed orchestrator tools"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from factory_automation.factory_agents.orchestrator_v3_agentic import (
    AgenticOrchestratorV3,
)
from factory_automation.factory_database.vector_db import ChromaDBClient

import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")


async def test_orchestrator_tools():
    """Test that orchestrator tools are properly registered"""

    print("\n" + "=" * 60)
    print("TESTING ORCHESTRATOR V3 TOOLS")
    print("=" * 60)

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ OPENAI_API_KEY not found!")
        return

    # Initialize
    print("\n📦 Initializing orchestrator...")
    chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
    orchestrator = AgenticOrchestratorV3(chroma_client)

    print(f"\n✅ Orchestrator initialized with {len(orchestrator.tools)} tools")

    # List all tools
    print("\n📋 Available tools:")
    for i, tool in enumerate(orchestrator.tools, 1):
        print(f"   {i}. {tool.name} - {tool.description}")

    # Test processing an email
    print("\n🧪 Testing email processing...")
    test_email = {
        "from": "test@example.com",
        "subject": "Order for 500 black tags",
        "body": "We need 500 black woven tags with silver thread. Urgent delivery required.",
        "message_id": "test_001",
    }

    result = await orchestrator.process_email(test_email)

    print("\n📊 Results:")
    print(f"   Success: {result['success']}")
    print(f"   Tools used: {result.get('autonomous_actions', 0)}")

    if result.get("tool_calls"):
        print("\n🔧 Tool usage:")
        for call in result["tool_calls"]:
            print(f"   - {call['tool']}")

    if result.get("final_summary"):
        print("\n📝 Summary:")
        print(f"   {result['final_summary'][:200]}...")

    print("\n✅ Test complete!")


if __name__ == "__main__":
    asyncio.run(test_orchestrator_tools())
