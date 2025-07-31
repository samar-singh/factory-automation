"""Gmail Agent - Polls and extracts order information from emails"""

import base64
import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .base import BaseAgent

logger = logging.getLogger(__name__)


class GmailAgent(BaseAgent):
    """Agent that polls Gmail for order emails and extracts order information"""

    def __init__(
        self, name: str = "GmailAgent", credentials_path: str = "gmail_credentials.json"
    ):
        instructions = """You are a Gmail agent that polls for order emails and extracts order information.
        You can connect to Gmail using service account credentials, search for emails matching order patterns,
        and extract customer details, item requirements, quantities, and urgency levels from email content."""

        super().__init__(name, instructions)
        self.credentials_path = credentials_path
        self.service = None
        self.user_email = None  # Will be set based on config

    def initialize_service(self, delegated_email: str):
        """Initialize Gmail service with delegated credentials"""
        try:
            # Load credentials
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            )

            # Delegate to the user's email
            delegated_credentials = credentials.with_subject(delegated_email)

            # Build service
            self.service = build("gmail", "v1", credentials=delegated_credentials)
            self.user_email = delegated_email

            logger.info(f"Gmail service initialized for {delegated_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            return False

    def list_messages(
        self, query: str = "", max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """List messages matching the query"""
        try:
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )

            messages = results.get("messages", [])
            return messages

        except HttpError as error:
            logger.error(f"An error occurred: {error}")
            return []

    def get_message(self, msg_id: str) -> Optional[Dict[str, Any]]:
        """Get full message details"""
        try:
            message = (
                self.service.users().messages().get(userId="me", id=msg_id).execute()
            )

            return message

        except HttpError as error:
            logger.error(f"An error occurred getting message: {error}")
            return None

    def extract_message_content(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Extract relevant content from Gmail message"""

        # Extract headers
        headers = {}
        for header in message["payload"].get("headers", []):
            headers[header["name"]] = header["value"]

        # Extract body
        body = self._extract_body(message["payload"])

        # Extract date
        date = headers.get("Date", "")

        return {
            "id": message["id"],
            "thread_id": message["threadId"],
            "from": headers.get("From", ""),
            "to": headers.get("To", ""),
            "subject": headers.get("Subject", ""),
            "date": date,
            "body": body,
            "snippet": message.get("snippet", ""),
        }

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Recursively extract body from email payload"""
        body = ""

        # Check if this part has a body
        if "body" in payload and "data" in payload["body"]:
            data = payload["body"]["data"]
            body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            return body

        # If multipart, recursively check parts
        if "parts" in payload:
            for part in payload["parts"]:
                part_body = self._extract_body(part)
                if part_body:
                    body += part_body + "\n"

        return body

    def extract_order_details(self, email_content: Dict[str, Any]) -> Dict[str, Any]:
        """Extract order details from email content using patterns"""

        body = email_content["body"]
        subject = email_content["subject"]

        # Extract customer info
        customer_name = self._extract_customer_name(email_content["from"])

        # Extract items - look for patterns
        items = self._extract_items(body)

        # Extract quantities
        quantities = self._extract_quantities(body)

        # Extract urgency
        urgency = self._extract_urgency(body)

        return {
            "email_id": email_content["id"],
            "customer_name": customer_name,
            "customer_email": email_content["from"],
            "subject": subject,
            "items": items,
            "quantities": quantities,
            "urgency": urgency,
            "raw_body": body[:500] + "..." if len(body) > 500 else body,
            "date": email_content["date"],
        }

    def _extract_customer_name(self, from_field: str) -> str:
        """Extract customer name from From field"""
        # Pattern: "Name <email@domain.com>"
        match = re.match(r'"?([^"<]+)"?\s*<?([^>]+)>?', from_field)
        if match:
            return match.group(1).strip()
        return from_field.split("@")[0]

    def _extract_items(self, body: str) -> List[str]:
        """Extract item descriptions from email body"""
        items = []

        # Common patterns for items
        patterns = [
            r"(?:need|require|order|want)\s+(.+?tags?)",
            r"(\w+\s+\w+\s+tags?)",
            r"tags?\s+for\s+(.+?)(?:\.|,|\n)",
            r"(\w+\s+(?:SOLLY|ENGLAND|MYNTRA|LIFESTYLE)\s+.+?)(?:\.|,|\n|$)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, body, re.IGNORECASE)
            items.extend(matches)

        # Clean and deduplicate
        cleaned_items = []
        for item in items:
            cleaned = " ".join(item.split())
            if len(cleaned) > 5 and cleaned not in cleaned_items:
                cleaned_items.append(cleaned)

        return cleaned_items[:5]  # Return top 5 unique items

    def _extract_quantities(self, body: str) -> Dict[str, int]:
        """Extract quantities from email body"""
        quantities = {}

        # Patterns for quantities
        patterns = [
            r"(\d+)\s*(?:pcs?|pieces?|units?|nos?|tags?)",
            r"quantity[:\s]+(\d+)",
            r"qty[:\s]+(\d+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, body, re.IGNORECASE)
            for match in matches:
                qty = int(match)
                if 0 < qty < 10000:  # Reasonable quantity range
                    quantities[f"quantity_{len(quantities)+1}"] = qty

        return quantities

    def _extract_urgency(self, body: str) -> str:
        """Determine urgency level from email content"""
        urgent_keywords = ["urgent", "asap", "immediately", "today", "tomorrow"]
        moderate_keywords = ["soon", "week", "days"]

        body_lower = body.lower()

        for keyword in urgent_keywords:
            if keyword in body_lower:
                return "HIGH"

        for keyword in moderate_keywords:
            if keyword in body_lower:
                return "MEDIUM"

        return "NORMAL"

    def poll_recent_orders(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Poll for recent order emails"""

        # Calculate date for query
        after_date = (datetime.now() - timedelta(hours=hours)).strftime("%Y/%m/%d")

        # Build query - adjust based on your email patterns
        queries = [
            f"after:{after_date} subject:order",
            f"after:{after_date} subject:requirement",
            f"after:{after_date} subject:tag",
            f"after:{after_date} subject:urgent",
        ]

        all_orders = []

        for query in queries:
            messages = self.list_messages(query, max_results=5)

            for msg in messages:
                full_message = self.get_message(msg["id"])
                if full_message:
                    content = self.extract_message_content(full_message)
                    order_details = self.extract_order_details(content)
                    all_orders.append(order_details)

        # Deduplicate by email_id
        seen = set()
        unique_orders = []
        for order in all_orders:
            if order["email_id"] not in seen:
                seen.add(order["email_id"])
                unique_orders.append(order)

        return unique_orders

    def run(self, task: str) -> str:
        """Execute Gmail polling task"""

        # Extract email address from task if provided
        email_match = re.search(r"[\w\.-]+@[\w\.-]+", task)
        if email_match:
            email = email_match.group(0)
            if not self.initialize_service(email):
                return "Failed to initialize Gmail service"
        else:
            return "Please provide an email address to poll"

        # Poll recent orders
        orders = self.poll_recent_orders(hours=48)  # Last 48 hours

        if not orders:
            return "No order emails found in the last 48 hours"

        # Format response
        response = f"Found {len(orders)} order emails:\n\n"

        for i, order in enumerate(orders, 1):
            response += (
                f"{i}. From: {order['customer_name']} ({order['customer_email']})\n"
            )
            response += f"   Subject: {order['subject']}\n"
            response += f"   Date: {order['date']}\n"
            response += f"   Urgency: {order['urgency']}\n"

            if order["items"]:
                response += f"   Items: {', '.join(order['items'][:3])}\n"

            if order["quantities"]:
                response += f"   Quantities: {list(order['quantities'].values())}\n"

            response += "\n"

        return response
