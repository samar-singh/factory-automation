#!/usr/bin/env python3
"""Simple Gmail connection test."""

import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from factory_automation.factory_agents.gmail_agent_enhanced import GmailAgentEnhanced


def test_gmail_connection():
    """Test basic Gmail connection."""
    print("Testing Gmail connection...")

    gmail_agent = GmailAgentEnhanced()

    # Test with the email from .env
    delegated_email = "bills23@gmail.com"

    print(f"Attempting to connect to Gmail for: {delegated_email}")

    if gmail_agent.initialize_service(delegated_email):
        print("✅ Successfully connected to Gmail!")

        # Try to list some messages
        try:
            results = (
                gmail_agent.service.users()
                .messages()
                .list(userId="me", maxResults=5, q="is:unread")
                .execute()
            )

            messages = results.get("messages", [])
            print(f"\nFound {len(messages)} unread messages")

            if messages:
                # Get details of first message
                msg = (
                    gmail_agent.service.users()
                    .messages()
                    .get(userId="me", id=messages[0]["id"])
                    .execute()
                )

                # Extract subject
                headers = msg["payload"].get("headers", [])
                subject = next(
                    (h["value"] for h in headers if h["name"] == "Subject"),
                    "No Subject",
                )
                from_email = next(
                    (h["value"] for h in headers if h["name"] == "From"), "Unknown"
                )

                print("\nFirst unread message:")
                print(f"From: {from_email}")
                print(f"Subject: {subject}")

        except Exception as e:
            print(f"\n❌ Error reading messages: {str(e)}")
            print("\nThis might be due to domain delegation not being set up.")
            print("Please ensure:")
            print("1. Domain-wide delegation is enabled for the service account")
            print("2. The service account has Gmail API scopes")
            print("3. The email 'bills23@gmail.com' has authorized the service account")

    else:
        print("❌ Failed to connect to Gmail")
        print("\nCheck that:")
        print("1. gmail_credentials.json exists and is valid")
        print("2. The service account has proper permissions")


if __name__ == "__main__":
    test_gmail_connection()
