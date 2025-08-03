"""Mock Gmail Agent for testing without actual Gmail access."""

import json
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from .base import BaseAgent

logger = logging.getLogger(__name__)


class MockGmailAgent(BaseAgent):
    """Mock Gmail agent that simulates email behavior for testing."""

    def __init__(
        self,
        name: str = "MockGmailAgent",
        mock_emails_dir: str = "mock_emails",
    ):
        instructions = """You are a mock Gmail agent for testing purposes.
        You simulate email polling and return predefined test emails."""

        super().__init__(name, instructions)
        self.mock_emails_dir = Path(mock_emails_dir)
        self.mock_emails_dir.mkdir(exist_ok=True)
        self.processed_emails = set()
        self.service = self  # Mock service object
        self.user_email = None  # Will be set in initialize_service

        # Create sample emails if directory is empty
        if not list(self.mock_emails_dir.glob("*.json")):
            self._create_sample_emails()

    def initialize_service(self, delegated_email: str) -> bool:
        """Mock initialization - always succeeds."""
        logger.info(f"Mock Gmail initialized for {delegated_email}")
        self.user_email = delegated_email
        return True

    def _create_sample_emails(self):
        """Create sample email files for testing."""
        sample_emails = [
            {
                "id": "msg_001",
                "threadId": "thread_001",
                "from": "Allen Solly <orders@allensolly.com>",
                "to": self.user_email or "factory@example.com",
                "subject": "New Order - 500 Black Tags Required",
                "date": (datetime.now() - timedelta(hours=2)).isoformat(),
                "body": """Dear Factory Team,

We need to place an order for the following items:
- 500 Black woven tags with silver thread
- Size: 2x1 inches
- Material: Satin finish
- Delivery needed by next week

Please confirm availability and send quotation.

Best regards,
Allen Solly Team""",
                "attachments": [],
                "labels": ["INBOX", "UNREAD"],
            },
            {
                "id": "msg_002",
                "threadId": "thread_002",
                "from": "Myntra Sourcing <sourcing@myntra.com>",
                "to": self.user_email or "factory@example.com",
                "subject": "Urgent: Sustainable Tags Order",
                "date": (datetime.now() - timedelta(hours=1)).isoformat(),
                "body": """Hi,

Urgent requirement for eco-friendly tags:
1. Green recycled paper tags - 1000 pieces
2. Natural cotton thread
3. Myntra branding embossed
4. Need sample first

Attached Excel with detailed specifications.

Thanks,
Myntra Team""",
                "attachments": [
                    {
                        "filename": "myntra_tag_specs.xlsx",
                        "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        "size": 15420,
                        "data": None,  # Would contain base64 data in real scenario
                    }
                ],
                "labels": ["INBOX", "UNREAD", "IMPORTANT"],
            },
            {
                "id": "msg_003",
                "threadId": "thread_003",
                "from": "H&M India <orders@hm.com>",
                "to": self.user_email or "factory@example.com",
                "subject": "Payment Confirmation - UTR 3421567890",
                "date": (datetime.now() - timedelta(minutes=30)).isoformat(),
                "body": """Dear Partner,

Payment processed for Order #HM-2024-1234:
Amount: Rs. 45,000
UTR: 3421567890
Date: Today

Please confirm receipt and process the order.

H&M Finance Team""",
                "attachments": [],
                "labels": ["INBOX", "UNREAD"],
            },
            {
                "id": "msg_004",
                "threadId": "thread_001",
                "from": "Allen Solly <orders@allensolly.com>",
                "to": self.user_email or "factory@example.com",
                "subject": "Re: New Order - 500 Black Tags Required",
                "date": (datetime.now() - timedelta(minutes=15)).isoformat(),
                "body": """Following up on our previous email.

Can you also provide:
- 200 Blue tags with white text
- Same specifications as black tags

This is urgent, please prioritize.

Thanks""",
                "attachments": [],
                "labels": ["INBOX", "UNREAD"],
            },
            {
                "id": "msg_005",
                "threadId": "thread_004",
                "from": "Zara Operations <ops@zara.com>",
                "to": self.user_email or "factory@example.com",
                "subject": "Sample Request - Premium Leather Tags",
                "date": datetime.now().isoformat(),
                "body": """Hello,

We're exploring premium leather tags for our new collection:
- Genuine leather material
- Embossed logo
- Gold foil stamping
- Need 10 samples in different colors

Please share:
1. Sample images
2. Pricing for 5000 pieces
3. Lead time

Attached mood board for reference.

Best,
Zara Design Team""",
                "attachments": [
                    {
                        "filename": "leather_tag_mood_board.png",
                        "mimeType": "image/png",
                        "size": 245000,
                        "data": None,  # Would contain base64 image data
                    }
                ],
                "labels": ["INBOX", "UNREAD"],
            },
        ]

        # Save emails to files
        for email in sample_emails:
            email_file = self.mock_emails_dir / f"{email['id']}.json"
            with open(email_file, "w") as f:
                json.dump(email, f, indent=2)

        logger.info(
            f"Created {len(sample_emails)} sample emails in {self.mock_emails_dir}"
        )

    def users(self):
        """Mock users() method."""
        return self

    def messages(self):
        """Mock messages() method."""
        return self

    def list(self, userId: str, q: str = "", maxResults: int = 10):
        """Mock list() method that returns execute() method."""
        self._list_params = {"userId": userId, "q": q, "maxResults": maxResults}
        return self

    def get(self, userId: str, id: str):
        """Mock get() method."""
        self._get_params = {"userId": userId, "id": id}
        return self

    def execute(self):
        """Mock execute() method that returns appropriate response."""
        if hasattr(self, "_list_params"):
            # Return list of messages
            messages = []
            for email_file in self.mock_emails_dir.glob("*.json"):
                if email_file.stem not in self.processed_emails:
                    with open(email_file) as f:
                        email = json.load(f)

                    # Apply query filter if provided
                    q = self._list_params.get("q", "")
                    if "is:unread" in q and "UNREAD" not in email.get("labels", []):
                        continue
                    if "after:" in q:
                        # Simple date filtering (mock)
                        continue

                    messages.append({"id": email["id"], "threadId": email["threadId"]})

                    if len(messages) >= self._list_params.get("maxResults", 10):
                        break

            delattr(self, "_list_params")
            return {"messages": messages}

        elif hasattr(self, "_get_params"):
            # Return specific message
            msg_id = self._get_params["id"]
            email_file = self.mock_emails_dir / f"{msg_id}.json"

            if email_file.exists():
                with open(email_file) as f:
                    email = json.load(f)

                # Convert to Gmail API format
                headers = [
                    {"name": "From", "value": email["from"]},
                    {"name": "To", "value": email["to"]},
                    {"name": "Subject", "value": email["subject"]},
                    {"name": "Date", "value": email["date"]},
                ]

                # Mark as read
                self.processed_emails.add(msg_id)

                delattr(self, "_get_params")
                return {
                    "id": email["id"],
                    "threadId": email["threadId"],
                    "labelIds": email.get("labels", []),
                    "payload": {
                        "headers": headers,
                        "body": {"data": email["body"]},  # Should be base64 in real API
                        "parts": [],  # Simplified - attachments would go here
                    },
                }

            delattr(self, "_get_params")
            return {}

    def process_order_email(self, msg_id: str) -> Dict[str, Any]:
        """Process a mock order email."""
        email_file = self.mock_emails_dir / f"{msg_id}.json"

        if not email_file.exists():
            logger.error(f"Mock email {msg_id} not found")
            return {}

        with open(email_file) as f:
            email = json.load(f)

        # Extract order details (simplified)
        items = []
        quantities = {}

        # Simple pattern matching for items
        body_lower = email["body"].lower()
        if "black" in body_lower and "tag" in body_lower:
            items.append("Black woven tags with silver thread")
            quantities["Black tags"] = 500
        if "blue" in body_lower and "tag" in body_lower:
            items.append("Blue tags with white text")
            quantities["Blue tags"] = 200
        if "green" in body_lower and "recycled" in body_lower:
            items.append("Green recycled paper tags")
            quantities["Eco tags"] = 1000
        if "leather" in body_lower:
            items.append("Premium leather tags")
            quantities["Leather tags"] = 10  # samples

        # Determine email type
        email_type = "order"
        if "payment" in email["subject"].lower() or "utr" in body_lower:
            email_type = "payment"
        elif "sample" in email["subject"].lower():
            email_type = "sample_request"

        return {
            "message_id": email["id"],
            "thread_id": email["threadId"],
            "from": email["from"],
            "subject": email["subject"],
            "date": email["date"],
            "body": email["body"],
            "attachments": email.get("attachments", []),
            "email_type": email_type,
            "items": items,
            "quantities": quantities,
            "is_urgent": "urgent" in body_lower,
            "has_attachments": len(email.get("attachments", [])) > 0,
        }

    def add_mock_email(self, email_data: Dict[str, Any]):
        """Add a new mock email for testing."""
        email_id = f"msg_{random.randint(1000, 9999)}"
        email_data["id"] = email_id
        email_data["date"] = datetime.now().isoformat()
        email_data["labels"] = ["INBOX", "UNREAD"]

        email_file = self.mock_emails_dir / f"{email_id}.json"
        with open(email_file, "w") as f:
            json.dump(email_data, f, indent=2)

        logger.info(f"Added mock email: {email_id}")
        return email_id
