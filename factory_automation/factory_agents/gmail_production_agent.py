"""Production Gmail Agent with proper attachment handling"""

import base64
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)


class GmailProductionAgent:
    """Production Gmail agent that downloads attachments to disk"""

    def __init__(self, credentials_path: str, attachment_dir: Optional[str] = None):
        """Initialize Gmail API client

        Args:
            credentials_path: Path to service account credentials JSON
            attachment_dir: Directory to save attachments (defaults to temp dir)
        """
        self.credentials = service_account.Credentials.from_service_account_file(
            credentials_path, scopes=["https://www.googleapis.com/auth/gmail.readonly"]
        )
        self.service = build("gmail", "v1", credentials=self.credentials)

        # Set up attachment directory
        if attachment_dir:
            self.attachment_dir = Path(attachment_dir)
            self.attachment_dir.mkdir(parents=True, exist_ok=True)
        else:
            # Use system temp directory with a subfolder
            self.attachment_dir = (
                Path(tempfile.gettempdir()) / "factory_automation_attachments"
            )
            self.attachment_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Gmail agent initialized. Attachments will be saved to: {self.attachment_dir}"
        )

    def fetch_unread_orders(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """Fetch unread order emails with attachments

        Returns:
            List of email data dictionaries with attachment file paths
        """
        try:
            # Query for unread emails (you can customize this query)
            query = 'is:unread subject:(order OR purchase OR quotation OR "price tag")'

            response = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )

            messages = response.get("messages", [])
            processed_emails = []

            for message in messages:
                email_data = self._process_message(message["id"])
                if email_data:
                    processed_emails.append(email_data)

            logger.info(f"Fetched {len(processed_emails)} unread order emails")
            return processed_emails

        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []

    def _process_message(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Process a single email message and download attachments

        Args:
            message_id: Gmail message ID

        Returns:
            Email data dictionary with attachment file paths
        """
        try:
            # Get the full message
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id)
                .execute()
            )

            # Extract email metadata
            headers = message["payload"].get("headers", [])
            subject = next(
                (h["value"] for h in headers if h["name"] == "Subject"), "No Subject"
            )
            sender = next(
                (h["value"] for h in headers if h["name"] == "From"), "Unknown"
            )
            date_str = next((h["value"] for h in headers if h["name"] == "Date"), "")

            # Extract email body
            body = self._extract_body(message["payload"])

            # Process attachments
            attachments = self._download_attachments(message_id, message["payload"])

            # Create email data with file paths
            email_data = {
                "message_id": message_id,
                "subject": subject,
                "from": sender,
                "date": date_str,
                "body": body,
                "attachments": attachments,  # List of file paths
                "email_type": "order",  # Can be determined by AI later
            }

            # Mark as read after processing
            self._mark_as_read(message_id)

            return email_data

        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}")
            return None

    def _extract_body(self, payload: Dict) -> str:
        """Extract email body from payload"""
        body = ""

        # Check for multipart
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    data = part["body"].get("data", "")
                    if data:
                        body += base64.urlsafe_b64decode(data).decode(
                            "utf-8", errors="ignore"
                        )
                elif part["mimeType"] == "text/html" and not body:
                    # Use HTML as fallback if no plain text
                    data = part["body"].get("data", "")
                    if data:
                        html_content = base64.urlsafe_b64decode(data).decode(
                            "utf-8", errors="ignore"
                        )
                        # Simple HTML to text (in production, use BeautifulSoup)
                        import re

                        body = re.sub("<[^<]+?>", "", html_content)
        else:
            # Single part message
            data = payload["body"].get("data", "")
            if data:
                body = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

        return body.strip()

    def _download_attachments(
        self, message_id: str, payload: Dict
    ) -> List[Dict[str, Any]]:
        """Download all attachments from an email to disk

        Args:
            message_id: Gmail message ID
            payload: Email payload

        Returns:
            List of attachment info with file paths
        """
        attachments = []

        # Create message-specific directory
        message_dir = (
            self.attachment_dir
            / f"msg_{message_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        message_dir.mkdir(parents=True, exist_ok=True)

        # Process parts for attachments
        parts = payload.get("parts", [])
        for part in parts:
            filename = part.get("filename")
            if filename:
                # This part is an attachment
                attachment_id = part["body"].get("attachmentId")
                if attachment_id:
                    # Download the attachment
                    attachment_data = (
                        self.service.users()
                        .messages()
                        .attachments()
                        .get(userId="me", messageId=message_id, id=attachment_id)
                        .execute()
                    )

                    # Decode and save to file
                    file_data = base64.urlsafe_b64decode(attachment_data["data"])
                    file_path = message_dir / filename

                    with open(file_path, "wb") as f:
                        f.write(file_data)

                    # Determine MIME type
                    mime_type = part.get("mimeType", "application/octet-stream")

                    # Add to attachments list
                    attachments.append(
                        {
                            "filename": filename,
                            "filepath": str(file_path.absolute()),
                            "mime_type": mime_type,
                            "size_bytes": len(file_data),
                        }
                    )

                    logger.info(
                        f"Downloaded attachment: {filename} ({len(file_data)} bytes) to {file_path}"
                    )

        return attachments

    def _mark_as_read(self, message_id: str):
        """Mark an email as read"""
        try:
            self.service.users().messages().modify(
                userId="me", id=message_id, body={"removeLabelIds": ["UNREAD"]}
            ).execute()
            logger.debug(f"Marked message {message_id} as read")
        except Exception as e:
            logger.error(f"Error marking message as read: {e}")

    def cleanup_old_attachments(self, days_old: int = 7):
        """Clean up old attachment files

        Args:
            days_old: Delete attachments older than this many days
        """
        import shutil
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(days=days_old)

        for msg_dir in self.attachment_dir.iterdir():
            if msg_dir.is_dir():
                # Check directory modification time
                dir_mtime = datetime.fromtimestamp(msg_dir.stat().st_mtime)
                if dir_mtime < cutoff_time:
                    try:
                        shutil.rmtree(msg_dir)
                        logger.info(f"Deleted old attachment directory: {msg_dir}")
                    except Exception as e:
                        logger.error(f"Error deleting {msg_dir}: {e}")
