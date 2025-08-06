#!/usr/bin/env python3
"""Simple test of the agentic system"""

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(str(Path(__file__).parent))

import logging

from factory_automation.factory_agents.orchestrator_v3_simple import (
    SimpleAgenticOrchestrator,
)
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_utils.trace_monitor import trace_monitor

logging.basicConfig(level=logging.INFO, format="%(message)s")


async def main():
    print("\n" + "=" * 60)
    print("🚀 SIMPLE AGENTIC TEST")
    print("=" * 60)

    # Check API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ ERROR: OPENAI_API_KEY not found!")
        print("Please ensure your .env file contains OPENAI_API_KEY")
        return

    # Initialize
    print("\n1️⃣ Initializing...")
    chroma_client = ChromaDBClient()
    orchestrator = SimpleAgenticOrchestrator(chroma_client)

    # Create test email
    test_email = {
        "from": "customer@example.com",
        "subject": "Urgent order - 500 black tags",
        "body": "Hi, we urgently need 500 black tags with silver thread. Please send quotation ASAP.",
        "message_id": "test_001",
    }

    print("\n2️⃣ Test Email:")
    print(f"   Subject: {test_email['subject']}")
    print(f"   Body: {test_email['body']}")

    print("\n3️⃣ Processing with AI...")
    print("   (AI will autonomously use tools)\n")

    # Process
    result = await orchestrator.process_email(test_email)

    print("\n4️⃣ Results:")
    if result["success"]:
        print("   ✅ Success!")
        print(f"   Trace: {result['trace_name']}")
        print("\n   AI Output:")
        print(f"   {result['result']}")
    else:
        print(f"   ❌ Error: {result['error']}")

    # Show trace
    print("\n5️⃣ Trace Summary:")
    summary = trace_monitor.get_trace_summary()
    print(f"   Total traces: {summary['total_traces']}")
    print(f"   Tool calls: {summary['tool_usage']}")

    print("\n✅ Test Complete!")
    print("\nView full traces at: https://platform.openai.com/traces")


if __name__ == "__main__":
    asyncio.run(main())
