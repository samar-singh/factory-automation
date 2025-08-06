#!/usr/bin/env python3
"""Simple test script to demonstrate the agentic system with mock emails"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

import logging

from factory_automation.factory_agents.mock_gmail_agent import MockGmailAgent
from factory_automation.factory_agents.orchestrator_v3_agentic import (
    AgenticOrchestratorV3,
)
from factory_automation.factory_database.vector_db import ChromaDBClient
from factory_automation.factory_utils.trace_monitor import trace_monitor

logging.basicConfig(level=logging.INFO, format="%(message)s")


async def test_mock_email_processing():
    """Test the agentic system with a mock email"""

    print("\n" + "=" * 60)
    print("🚀 TESTING AGENTIC ORCHESTRATOR WITH MOCK EMAIL")
    print("=" * 60)

    # Step 1: Initialize the system
    print("\n1️⃣ Initializing system components...")
    chroma_client = ChromaDBClient(collection_name="tag_inventory_stella")
    orchestrator = AgenticOrchestratorV3(chroma_client)
    print("✅ Orchestrator ready with ChromaDB")

    # Step 2: Get a mock email
    print("\n2️⃣ Getting mock email...")
    mock_agent = MockGmailAgent()
    mock_agent.initialize_service("test@factory.com")

    # Get the first unread email
    messages = (
        mock_agent.users()
        .messages()
        .list(userId="me", q="is:unread", maxResults=1)
        .execute()
    )

    if not messages.get("messages"):
        print("❌ No mock emails found!")
        return

    # Process the email to get structured data
    email_data = mock_agent.process_order_email(messages["messages"][0]["id"])

    print("📧 Found email:")
    print(f"   From: {email_data.get('from', 'Unknown')}")
    print(f"   Subject: {email_data.get('subject', 'No subject')}")
    print(f"   Type: {email_data.get('email_type', 'unknown')}")
    print(f"   Body preview: {email_data.get('body', '')[:100]}...")

    # Step 3: Let the AI process autonomously
    print("\n3️⃣ Processing with AI (autonomous mode)...")
    print("   The AI will decide which tools to use:\n")

    result = await orchestrator.process_email(email_data)

    # Step 4: Show results
    print("\n4️⃣ Processing Results:")
    print("   " + "-" * 50)

    if result["success"]:
        print(
            f"   ✅ Success! AI made {result.get('autonomous_actions', 0)} tool calls"
        )

        # Show tool sequence
        if result.get("tool_calls"):
            print("\n   🔧 Tools Used (in order):")
            for i, call in enumerate(result["tool_calls"], 1):
                print(f"      {i}. {call['tool']}")
                # Show key results
                if call["tool"] == "analyze_email":
                    print(
                        f"         → Type: {call['result'].get('email_type', 'unknown')}"
                    )
                elif call["tool"] == "search_inventory":
                    matches = call["result"]
                    if matches:
                        print(f"         → Found {len(matches)} matches")
                        print(
                            f"         → Best: {matches[0]['name']} ({matches[0]['similarity_score']:.1%})"
                        )
                elif call["tool"] == "make_decision":
                    print(
                        f"         → Decision: {call['result'].get('decision', 'unknown')}"
                    )
                elif call["tool"] == "generate_document":
                    print(
                        f"         → Generated: {call['result'].get('type', 'unknown')}"
                    )

        print("\n   📝 AI Summary:")
        print(f"   {result.get('final_summary', 'No summary')}")

    else:
        print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")

    # Step 5: View trace details
    print("\n5️⃣ Trace Information:")
    print(f"   Trace Name: {result.get('trace_name', 'Unknown')}")
    print("   View in OpenAI: https://platform.openai.com/traces")

    # Show local trace summary
    trace_summary = trace_monitor.get_trace_summary()
    print("\n   📊 Local Trace Stats:")
    print(f"   Total tool calls: {sum(trace_summary['tool_usage'].values())}")
    print(f"   Tools used: {', '.join(trace_summary['tool_usage'].keys())}")


async def main():
    """Main function"""
    print("\n🎯 MOCK EMAIL TEST SYSTEM")
    print("This demonstrates how the AI autonomously processes emails\n")

    print("Available mock emails:")
    print("1. Allen Solly - Order for 500 black tags")
    print("2. Myntra - Urgent sustainable tags order")
    print("3. H&M - Payment confirmation")
    print("4. Zara - Sample request for leather tags")

    print("\nThe AI will:")
    print("• Analyze the email type")
    print("• Extract order details")
    print("• Search inventory using ChromaDB")
    print("• Make approval decisions")
    print("• Generate documents")

    print("\nStarting test...")

    await test_mock_email_processing()

    print("\n" + "=" * 60)
    print("✅ Test Complete!")
    print("\nNext steps:")
    print("1. Run 'python test_agentic_orchestrator.py' for more options")
    print("2. Check traces at https://platform.openai.com/traces")
    print("3. Modify mock emails in 'mock_emails/' directory")


if __name__ == "__main__":
    asyncio.run(main())
