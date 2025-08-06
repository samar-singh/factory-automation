#!/usr/bin/env python3
"""Test email monitoring functionality."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from factory_automation.factory_agents.email_monitor_agent import EmailMonitorAgent
from factory_automation.factory_agents.orchestrator_v2_agent import OrchestratorAgentV2
from factory_automation.factory_config.settings import settings
from factory_automation.factory_database.vector_db import ChromaDBClient

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def test_email_check():
    """Test checking for new emails."""
    logger.info("Testing email check functionality...")

    # Initialize email monitor
    email_monitor = EmailMonitorAgent()

    # Check for new emails
    new_emails = await email_monitor.check_new_emails()

    if new_emails:
        logger.info(f"Found {len(new_emails)} new emails:")
        for email in new_emails:
            logger.info(f"  - From: {email.get('from', 'Unknown')}")
            logger.info(f"    Subject: {email.get('subject', 'No subject')}")
            logger.info(f"    Items: {len(email.get('items', []))}")
    else:
        logger.info("No new emails found")


async def test_email_monitoring():
    """Test the complete email monitoring loop."""
    logger.info("Testing email monitoring loop...")

    # Initialize ChromaDB
    chroma_client = ChromaDBClient()

    # Initialize orchestrator
    orchestrator = OrchestratorAgentV2(chroma_client)

    # Override poll interval for testing
    logger.info(
        "Starting email monitoring (will check every 30 seconds for testing)..."
    )

    # Modify the monitoring to use shorter interval
    orchestrator.is_monitoring = True

    try:
        for i in range(3):  # Check 3 times
            logger.info(f"\nCheck #{i+1}")

            # Check for new emails
            new_emails = await orchestrator.email_monitor.check_new_emails()

            for email in new_emails:
                logger.info(f"Processing email: {email.get('subject', 'No subject')}")
                result = await orchestrator.process_email(email)
                logger.info(f"Result: {result}")

            if i < 2:  # Don't wait after last check
                logger.info("Waiting 30 seconds before next check...")
                await asyncio.sleep(30)

    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user")
    finally:
        orchestrator.is_monitoring = False


async def main():
    """Main test function."""
    print("\nEmail Monitoring Test")
    print("=" * 50)
    print("1. Test single email check")
    print("2. Test email monitoring loop (90 seconds)")
    print("3. Exit")

    choice = input("\nSelect option: ")

    if choice == "1":
        await test_email_check()
    elif choice == "2":
        await test_email_monitoring()
    else:
        print("Exiting...")


if __name__ == "__main__":
    # Check if Gmail credentials are configured
    if not settings.gmail_delegated_email:
        print("\nERROR: GMAIL_DELEGATED_EMAIL not configured in .env file")
        print("Please add: GMAIL_DELEGATED_EMAIL=your-email@company.com")
        print(
            "\nNote: The email must have domain-wide delegation enabled for the service account"
        )
        sys.exit(1)

    # Check if service account credentials exist
    from pathlib import Path

    if not Path("gmail_credentials.json").exists():
        print("\nERROR: gmail_credentials.json not found!")
        print(
            "Please ensure your service account credentials file is in the project root"
        )
        sys.exit(1)

    asyncio.run(main())
