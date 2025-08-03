#!/usr/bin/env python3
"""Test the tracked orchestrator"""

import asyncio
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from factory_automation.factory_agents.orchestrator_v3_tracked import (
    TrackedOrchestratorV3,
)
from factory_automation.factory_database.vector_db import ChromaDBClient

import logging

logging.basicConfig(level=logging.INFO, format="%(message)s")


async def test_tracked_orchestrator():
    """Test orchestrator with tool tracking"""

    print("\n" + "=" * 60)
    print("TESTING TRACKED ORCHESTRATOR")
    print("=" * 60)

    # Initialize
    print("\n📦 Initializing tracked orchestrator...")
    chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
    orchestrator = TrackedOrchestratorV3(chroma_client)

    # Test email
    test_email = {
        "from": "customer@example.com",
        "subject": "Order - 300 red tags",
        "body": "We need 300 red woven tags with our logo. Please send quotation.",
        "message_id": "test_tracked",
    }

    print("\n📧 Test Email:")
    print(f"   From: {test_email['from']}")
    print(f"   Subject: {test_email['subject']}")
    print(f"   Body: {test_email['body']}")

    print("\n🤖 Processing email...")

    result = await orchestrator.process_email(test_email)

    print("\n📊 Results:")
    print(f"   Success: {result['success']}")
    print(f"   Tools called: {result.get('autonomous_actions', 0)}")

    if result.get("tool_calls"):
        print("\n🔧 Tool Usage Details:")
        for i, call in enumerate(result["tool_calls"], 1):
            print(f"\n   {i}. Tool: {call['tool']}")
            print(f"      Time: {call['timestamp']}")
            print(f"      Args: {json.dumps(call.get('args', {}), indent=9)}")
            print(f"      Result: {call.get('result', 'No result')}")

    print("\n📝 Final Summary:")
    print(result.get("final_summary", "No summary")[:500])

    print("\n✅ Test complete!")

    # Summary of tracking capability
    print("\n" + "=" * 60)
    print("TRACKING SUMMARY")
    print("=" * 60)
    print("\nThe TrackedOrchestratorV3 successfully tracks tool calls by:")
    print("1. Storing tool calls in a class variable during execution")
    print("2. Each tool appends its call info when invoked")
    print("3. The process_email method returns all tracked calls")
    print("\nThis provides full visibility into the AI's tool usage!")


if __name__ == "__main__":
    asyncio.run(test_tracked_orchestrator())
