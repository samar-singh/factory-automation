"""Email monitoring agent for Gmail integration."""

import logging
from datetime import datetime
from typing import Any, Dict, List

from ..factory_config.settings import settings
from .base import BaseAgent
from .gmail_agent_enhanced import GmailAgentEnhanced
from .mock_gmail_agent import MockGmailAgent

logger = logging.getLogger(__name__)


class EmailMonitorAgent(BaseAgent):
    """Agent responsible for monitoring and processing emails."""

    def __init__(self):
        """Initialize email monitor agent."""
        super().__init__(
            name="Email Monitor",
            instructions="""You are responsible for monitoring Gmail for new order emails.
            Identify email types: new_order, payment, follow_up, or other.
            Extract key information: sender, subject, attachments, and intent.""",
        )
        # Use mock agent if configured or if no delegated email
        use_mock = getattr(settings, "use_mock_gmail", False)
        if use_mock or not getattr(settings, "gmail_delegated_email", None):
            logger.info("Using Mock Gmail Agent for testing")
            self.gmail_agent = MockGmailAgent()
        else:
            logger.info("Using Real Gmail Agent")
            self.gmail_agent = GmailAgentEnhanced()

        self.last_check_time = datetime.now()

    async def check_new_emails(self) -> List[Dict[str, Any]]:
        """Check for new emails in Gmail.

        Returns:
            List of new email dictionaries
        """
        try:
            # Initialize Gmail service with delegated email
            delegated_email = getattr(settings, "gmail_delegated_email", None)
            if not delegated_email:
                logger.warning("No delegated email configured")
                return []

            if not self.gmail_agent.initialize_service(delegated_email):
                logger.error("Failed to initialize Gmail service")
                return []

            # Search for emails since last check
            query = f"after:{int(self.last_check_time.timestamp())} label:INBOX"

            # Get message list
            results = (
                self.gmail_agent.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=10)
                .execute()
            )

            messages = results.get("messages", [])
            new_emails = []

            for msg in messages:
                try:
                    # Process each email
                    email_data = self.gmail_agent.process_order_email(msg["id"])
                    if email_data:
                        new_emails.append(email_data)
                except Exception as e:
                    logger.error(f"Error processing email {msg['id']}: {str(e)}")

            # Update last check time
            self.last_check_time = datetime.now()

            if new_emails:
                logger.info(f"Found {len(new_emails)} new emails")

            return new_emails

        except Exception as e:
            logger.error(f"Error checking emails: {str(e)}")
            return []
