"""Email monitoring agent for Gmail integration."""

import logging
from typing import Any, Dict, List

from factory_agents.base import BaseAgent

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

    async def check_new_emails(self) -> List[Dict[str, Any]]:
        """Check for new emails in Gmail.

        Returns:
            List of new email dictionaries
        """
        # TODO: Implement Gmail API integration
        logger.info("Checking for new emails...")
        return []
