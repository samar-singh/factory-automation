#!/usr/bin/env python3
"""Complete System Test - Tests the entire factory automation flow"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(str(Path(__file__).parent))

import logging

from factory_automation.factory_agents.mock_gmail_agent import MockGmailAgent
from factory_automation.factory_agents.orchestrator_v3_simple import (
    SimpleAgenticOrchestrator,
)
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_utils.trace_monitor import trace_monitor

logging.basicConfig(level=logging.INFO, format="%(message)s")


async def test_complete_flow():
    """Test the complete email → processing → decision flow"""

    print("\n" + "=" * 80)
    print("🏭 FACTORY AUTOMATION COMPLETE SYSTEM TEST")
    print("=" * 80)

    # Check prerequisites
    print("\n📋 Checking prerequisites...")
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not found in .env")
        return
    print("✅ OpenAI API key found")

    if not Path("chroma_data").exists():
        print("⚠️  ChromaDB data not found - will use mock data")
    else:
        print("✅ ChromaDB data found")

    # Initialize components
    print("\n🔧 Initializing system components...")

    # 1. ChromaDB
    print("  • Initializing ChromaDB...")
    chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")

    # 2. Orchestrator
    print("  • Initializing AI Orchestrator...")
    orchestrator = SimpleAgenticOrchestrator(chroma_client)

    # 3. Mock Gmail
    print("  • Initializing Mock Gmail...")
    gmail = MockGmailAgent()
    gmail.initialize_service("factory@example.com")

    print("\n✅ All components initialized!")

    # Get available emails
    print("\n📧 Available mock emails:")
    messages = (
        gmail.users()
        .messages()
        .list(userId="me", q="is:unread", maxResults=10)
        .execute()
    )

    emails = []
    for i, msg in enumerate(messages.get("messages", [])[:5], 1):
        email_data = gmail.process_order_email(msg["id"])
        emails.append(email_data)
        print(f"  {i}. {email_data['from']} - {email_data['subject']}")

    # Process each email
    print("\n🚀 Processing emails with AI orchestrator...")
    print("  (AI will autonomously decide how to handle each email)\n")

    for i, email in enumerate(emails[:3], 1):  # Process first 3
        print(f"\n{'='*60}")
        print(f"📧 Email {i}/3: {email['subject']}")
        print(f"{'='*60}")

        # Show email details
        print(f"From: {email['from']}")
        print(f"Type: {email.get('email_type', 'Unknown')}")
        print(f"Body preview: {email['body'][:100]}...")

        # Process with AI
        print("\n🤖 AI Processing...")
        start_time = datetime.now()

        result = await orchestrator.process_email(email)

        processing_time = (datetime.now() - start_time).total_seconds()

        # Show results
        if result["success"]:
            print(f"\n✅ Success! (Processed in {processing_time:.1f}s)")

            # Extract key information from AI output
            ai_output = result["result"]

            if "Order" in ai_output:
                print("\n📦 Order Details:")
                if "500" in ai_output:
                    print("  • Quantity: 500")
                if "Black" in ai_output:
                    print("  • Item: Black tags")
                if "Urgent" in ai_output:
                    print("  • Priority: Urgent")

            if "Match" in ai_output and "%" in ai_output:
                print("\n🔍 Inventory Match:")
                # Extract match info
                import re

                match = re.search(r"(\d+)%", ai_output)
                if match:
                    print(f"  • Confidence: {match.group(1)}%")
                if "Black Woven Tag" in ai_output:
                    print("  • Best match: Black Woven Tag")

            if "Decision" in ai_output:
                print("\n⚖️ AI Decision:")
                if "Auto-approved" in ai_output:
                    print("  • ✅ Auto-approved")
                elif "manual review" in ai_output:
                    print("  • 👤 Needs manual review")
                else:
                    print("  • ❓ Needs clarification")

            print(f"\n📊 Trace: {result['trace_name']}")

        else:
            print(f"\n❌ Failed: {result.get('error', 'Unknown error')}")

        # Small delay between emails
        await asyncio.sleep(1)

    # Summary
    print("\n" + "=" * 80)
    print("📊 PROCESSING SUMMARY")
    print("=" * 80)

    trace_summary = trace_monitor.get_trace_summary()
    print(f"\nTotal emails processed: {trace_summary['total_traces']}")

    if trace_summary["tool_usage"]:
        print("\n🔧 AI Tools Used:")
        for tool, count in trace_summary["tool_usage"].items():
            print(f"  • {tool}: {count} times")

    # Show sample trace
    if trace_summary["recent_traces"]:
        print("\n📍 Sample Trace Flow:")
        trace = trace_summary["recent_traces"][0]
        print(f"  Email: {trace['name']}")
        print(f"  Duration: {trace['duration']:.1f}s")
        print(f"  Tool sequence: {' → '.join(trace['tool_sequence'])}")

    print("\n✅ Complete system test finished!")
    print("\n📈 View detailed traces at: https://platform.openai.com/traces")
    print("💡 Run 'python test_agentic_orchestrator.py' for more testing options")


async def main():
    """Main test runner"""
    print("\n🏭 FACTORY AUTOMATION SYSTEM")
    print("Complete End-to-End Test")
    print("\nThis test will:")
    print("• Process multiple mock emails")
    print("• Show AI decision-making")
    print("• Demonstrate tool usage")
    print("• Display processing results")

    print("\nPress Enter to start the test...", end="")
    sys.stdin.read(1)  # Wait for Enter

    await test_complete_flow()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except EOFError:
        # Run without waiting for input
        asyncio.run(test_complete_flow())
