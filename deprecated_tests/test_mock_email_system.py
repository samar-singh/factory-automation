#!/usr/bin/env python3
"""Test the mock email system."""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from factory_automation.factory_agents.mock_gmail_agent import MockGmailAgent
from factory_automation.factory_agents.email_monitor_agent import EmailMonitorAgent
from factory_automation.factory_agents.orchestrator_v2_agent import OrchestratorAgentV2
from factory_automation.factory_database.vector_db import ChromaDBClient


def test_mock_gmail():
    """Test mock Gmail functionality."""
    print("\n" + "=" * 60)
    print("TESTING MOCK GMAIL SYSTEM")
    print("=" * 60)

    # Create mock agent
    mock_agent = MockGmailAgent()

    # Initialize (always succeeds for mock)
    if mock_agent.initialize_service("test@factory.com"):
        print("✅ Mock Gmail initialized")

    # List messages
    print("\n📧 Fetching mock emails...")
    results = (
        mock_agent.users()
        .messages()
        .list(userId="me", q="is:unread", maxResults=10)
        .execute()
    )

    messages = results.get("messages", [])
    print(f"Found {len(messages)} unread messages")

    # Process each message
    for msg in messages[:3]:  # First 3 messages
        print(f"\n--- Message {msg['id']} ---")

        # Get full message
        full_msg = (
            mock_agent.users().messages().get(userId="me", id=msg["id"]).execute()
        )

        # Extract headers
        headers = full_msg["payload"]["headers"]
        subject = next(
            (h["value"] for h in headers if h["name"] == "Subject"), "No Subject"
        )
        from_email = next(
            (h["value"] for h in headers if h["name"] == "From"), "Unknown"
        )

        print(f"From: {from_email}")
        print(f"Subject: {subject}")

        # Process as order
        order_data = mock_agent.process_order_email(msg["id"])
        print(f"Type: {order_data.get('email_type', 'unknown')}")
        print(f"Items: {order_data.get('items', [])}")
        print(f"Urgent: {order_data.get('is_urgent', False)}")


async def test_email_monitoring_with_mock():
    """Test email monitoring with mock system."""
    print("\n" + "=" * 60)
    print("TESTING EMAIL MONITORING WITH MOCK")
    print("=" * 60)

    # Create email monitor (will use mock automatically)
    email_monitor = EmailMonitorAgent()

    print("\n🔍 Checking for new emails...")
    new_emails = await email_monitor.check_new_emails()

    if new_emails:
        print(f"✅ Found {len(new_emails)} new emails")
        for email in new_emails:
            print(f"\n📧 Email: {email.get('subject', 'No subject')}")
            print(f"   From: {email.get('from', 'Unknown')}")
            print(f"   Type: {email.get('email_type', 'unknown')}")
            print(f"   Items: {len(email.get('items', []))}")
    else:
        print("No new emails found")


async def test_full_workflow_with_mock():
    """Test complete workflow with mock emails."""
    print("\n" + "=" * 60)
    print("TESTING FULL WORKFLOW WITH MOCK EMAILS")
    print("=" * 60)

    # Initialize components
    print("\n🔧 Initializing system...")
    chroma_client = ChromaDBClient()
    orchestrator = OrchestratorAgentV2(chroma_client)

    print("\n📧 Starting email monitoring loop (3 checks, 10 seconds apart)...")

    # Temporarily set monitoring flag
    orchestrator.is_monitoring = True

    for i in range(3):
        print(f"\n--- Check #{i+1} ---")

        # Check for new emails
        new_emails = await orchestrator.email_monitor.check_new_emails()

        if new_emails:
            print(f"Found {len(new_emails)} new emails")

            for email in new_emails[:1]:  # Process first email only
                print(f"\n🤖 AI Processing: {email.get('subject', 'No subject')}")

                # Process with AI orchestrator
                result = await orchestrator.process_email(email)

                print("\n📊 AI Analysis:")
                print(f"Success: {result.get('success', False)}")
                if result.get("success"):
                    print(f"Result: {json.dumps(result.get('result', {}), indent=2)}")
                else:
                    print(f"Error: {result.get('error', 'Unknown error')}")
        else:
            print("No new emails")

        if i < 2:  # Don't wait after last check
            print("\nWaiting 10 seconds...")
            await asyncio.sleep(10)

    orchestrator.is_monitoring = False
    print("\n✅ Test complete!")


def add_custom_mock_email():
    """Add a custom mock email for testing."""
    print("\n" + "=" * 60)
    print("ADD CUSTOM MOCK EMAIL")
    print("=" * 60)

    mock_agent = MockGmailAgent()

    # Create custom email
    custom_email = {
        "from": "Custom Brand <orders@custombrand.com>",
        "to": "factory@example.com",
        "subject": "Rush Order - 2000 Premium Tags",
        "body": """Urgent order requirement:

- 2000 premium satin tags
- Gold embossing with our logo
- Size: 3x2 inches
- Need delivery in 3 days
- Budget: Rs. 50,000

Please confirm ASAP.

Custom Brand Team""",
        "attachments": [],
        "threadId": "thread_custom",
    }

    email_id = mock_agent.add_mock_email(custom_email)
    print(f"✅ Added mock email with ID: {email_id}")
    print(f"📁 Saved to: mock_emails/{email_id}.json")


async def main():
    """Main test menu."""
    while True:
        print("\n" + "=" * 60)
        print("MOCK EMAIL SYSTEM TEST MENU")
        print("=" * 60)
        print("1. Test basic mock Gmail functionality")
        print("2. Test email monitoring with mock")
        print("3. Test full AI workflow with mock emails")
        print("4. Add custom mock email")
        print("5. Exit")

        choice = input("\nSelect option (1-5): ")

        if choice == "1":
            test_mock_gmail()
        elif choice == "2":
            await test_email_monitoring_with_mock()
        elif choice == "3":
            await test_full_workflow_with_mock()
        elif choice == "4":
            add_custom_mock_email()
        elif choice == "5":
            print("\nExiting...")
            break
        else:
            print("Invalid choice")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    # Ensure mock emails directory exists
    Path("mock_emails").mkdir(exist_ok=True)

    print("\n🎭 MOCK EMAIL SYSTEM")
    print("This allows testing the complete email workflow without Gmail access")
    print("Mock emails simulate real order emails from brands")

    asyncio.run(main())
