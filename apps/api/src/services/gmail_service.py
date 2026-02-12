"""Gmail API Service.

Provides functionality to:
- Fetch email content from Gmail API
- Extract sender information and email body
- Parse Gmail message responses
- Send reply emails via Gmail API
"""

import base64
import re
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Any, cast

import httpx

from src.utils.logging import get_logger

logger = get_logger(__name__)

GMAIL_API_BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailApiError(Exception):
    """Exception raised when Gmail API call fails."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


def extract_sender_info(from_header: str) -> tuple[str | None, str]:
    """Extract sender name and email from From header.

    Handles formats:
    - "Name <email@domain.com>"
    - "email@domain.com"

    Args:
        from_header: The From header value

    Returns:
        Tuple of (name, email) where name may be None
    """
    # Pattern: "Name <email@domain.com>"
    match = re.match(r"^(.+?)\s*<([^>]+)>$", from_header.strip())
    if match:
        name = match.group(1).strip().strip('"')
        email = match.group(2).strip()
        return name, email

    # Pattern: just "email@domain.com"
    return None, from_header.strip()


def get_header_value(headers: list[dict], name: str) -> str | None:
    """Get a specific header value from headers list.

    Args:
        headers: List of header dicts with 'name' and 'value' keys
        name: The header name to find

    Returns:
        Header value or None if not found
    """
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value")
    return None


def extract_email_body(payload: dict) -> str:
    """Extract email body text from Gmail message payload.

    Handles both plain text and multipart messages.
    Prefers text/plain over text/html.

    Args:
        payload: The 'payload' field from Gmail message

    Returns:
        Decoded email body text
    """
    mime_type = payload.get("mimeType", "")

    # Handle direct body (text/plain)
    if mime_type == "text/plain":
        body_data = payload.get("body", {}).get("data")
        if body_data:
            return base64.urlsafe_b64decode(body_data).decode("utf-8")

    # Handle multipart messages
    if mime_type.startswith("multipart/"):
        parts = payload.get("parts", [])

        # First, try to find text/plain part
        for part in parts:
            if part.get("mimeType") == "text/plain":
                body_data = part.get("body", {}).get("data")
                if body_data:
                    return base64.urlsafe_b64decode(body_data).decode("utf-8")

        # Then try text/html
        for part in parts:
            if part.get("mimeType") == "text/html":
                body_data = part.get("body", {}).get("data")
                if body_data:
                    return base64.urlsafe_b64decode(body_data).decode("utf-8")

        # Recursively check nested multipart
        for part in parts:
            if part.get("mimeType", "").startswith("multipart/"):
                result = extract_email_body(part)
                if result:
                    return result

    # Fallback: try body.data directly
    body_data = payload.get("body", {}).get("data")
    if body_data:
        return base64.urlsafe_b64decode(body_data).decode("utf-8")

    return ""


def parse_gmail_message(message: dict) -> dict:
    """Parse Gmail API message response into structured data.

    Args:
        message: Raw Gmail API message response

    Returns:
        Dict with extracted email fields
    """
    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    from_header = get_header_value(headers, "From") or ""
    sender_name, sender_email = extract_sender_info(from_header)

    # Parse internal date (milliseconds since epoch)
    internal_date = message.get("internalDate")
    received_at = None
    if internal_date:
        timestamp_seconds = int(internal_date) / 1000
        received_at = datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc)

    return {
        "google_message_id": message.get("id"),
        "thread_id": message.get("threadId"),
        "sender_email": sender_email,
        "sender_name": sender_name,
        "subject": get_header_value(headers, "Subject"),
        "original_body": extract_email_body(payload),
        "received_at": received_at,
    }


def get_message_id(message: dict) -> str | None:
    """Extract Message-ID header from a Gmail API message response.

    Args:
        message: Raw Gmail API message response

    Returns:
        Message-ID header value or None if not found
    """
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    return get_header_value(headers, "Message-ID")


class GmailApiClient:
    """Client for Gmail API HTTP operations."""

    def __init__(self, access_token: str):
        """Initialize client with access token.

        Args:
            access_token: Valid Gmail API access token
        """
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    async def fetch_email_history(
        self, start_history_id: str, label_id: str = "INBOX"
    ) -> dict[str, Any]:
        """Fetch email history changes from Gmail API.

        Args:
            start_history_id: History ID to start from
            label_id: Label to filter history (default: INBOX)

        Returns:
            Gmail history response

        Raises:
            GmailApiError: If API call fails
        """
        url = f"{GMAIL_API_BASE_URL}/history"
        params = {
            "startHistoryId": start_history_id,
            "labelId": label_id,
            "historyTypes": "messageAdded",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=self.headers, params=params, timeout=30.0
            )

            if response.status_code != 200:
                logger.error(
                    f"Gmail history API error: {response.status_code} - {response.text}"
                )
                raise GmailApiError(
                    f"Failed to fetch history: {response.text}",
                    status_code=response.status_code,
                )

            return cast(dict[str, Any], response.json())

    async def list_recent_messages(
        self, max_results: int = 10, label_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """List recent messages from Gmail inbox.

        This is an alternative to fetch_email_history that directly
        lists messages, which is more reliable when historyId tracking
        is not available.

        Args:
            max_results: Maximum number of messages to return
            label_ids: Labels to filter by (default: INBOX, UNREAD)

        Returns:
            List of message metadata (id, threadId)

        Raises:
            GmailApiError: If API call fails
        """
        if label_ids is None:
            label_ids = ["INBOX"]

        url = f"{GMAIL_API_BASE_URL}/messages"

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=self.headers,
                params={"maxResults": max_results, "labelIds": label_ids},
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(
                    f"Gmail messages.list API error: {response.status_code} - {response.text}"
                )
                raise GmailApiError(
                    f"Failed to list messages: {response.text}",
                    status_code=response.status_code,
                )

            data = cast(dict[str, Any], response.json())
            return cast(list[dict[str, Any]], data.get("messages", []))

    async def fetch_message(self, message_id: str) -> dict[str, Any]:
        """Fetch a specific email message from Gmail API.

        Args:
            message_id: The Gmail message ID

        Returns:
            Gmail message response

        Raises:
            GmailApiError: If API call fails
        """
        url = f"{GMAIL_API_BASE_URL}/messages/{message_id}"
        params = {"format": "full"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=self.headers, params=params, timeout=30.0
            )

            if response.status_code != 200:
                logger.error(
                    f"Gmail message API error: {response.status_code} - {response.text}"
                )
                raise GmailApiError(
                    f"Failed to fetch message: {response.text}",
                    status_code=response.status_code,
                )

            return cast(dict[str, Any], response.json())

    async def fetch_thread(self, thread_id: str) -> dict[str, Any]:
        """Fetch a thread with metadata from Gmail API.

        Args:
            thread_id: The Gmail thread ID

        Returns:
            Gmail thread response with messages metadata

        Raises:
            GmailApiError: If API call fails
        """
        url = f"{GMAIL_API_BASE_URL}/threads/{thread_id}"
        params = {"format": "metadata"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=self.headers, params=params, timeout=30.0
            )

            if response.status_code != 200:
                logger.error(
                    f"Gmail thread API error: {response.status_code} - {response.text}"
                )
                raise GmailApiError(
                    f"Failed to fetch thread: {response.text}",
                    status_code=response.status_code,
                )

            return cast(dict[str, Any], response.json())

    async def search_messages(
        self,
        query: str,
        max_results: int = 30,
    ) -> list[dict[str, Any]]:
        """Search messages using Gmail API query.

        Args:
            query: Gmail search query (e.g., "from:email@example.com")
            max_results: Maximum number of messages to return

        Returns:
            List of message metadata (id, threadId)

        Raises:
            GmailApiError: If API call fails
        """
        url = f"{GMAIL_API_BASE_URL}/messages"
        params = {
            "q": query,
            "maxResults": max_results,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=self.headers, params=params, timeout=30.0
            )

            if response.status_code != 200:
                logger.error(
                    f"Gmail search API error: {response.status_code} - {response.text}"
                )
                raise GmailApiError(
                    f"Failed to search messages: {response.text}",
                    status_code=response.status_code,
                )

            data = cast(dict[str, Any], response.json())
            return cast(list[dict[str, Any]], data.get("messages", []))

    async def send_message(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: str,
        in_reply_to: str,
        references: str,
    ) -> dict[str, Any]:
        """Send a reply email via Gmail API.

        Constructs a MIME message with reply headers and sends it
        using Gmail API messages.send endpoint.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            thread_id: Gmail thread ID to reply in
            in_reply_to: Message-ID of the original email
            references: References header value

        Returns:
            Gmail API response (id, threadId, labelIds)

        Raises:
            GmailApiError: If API call fails
        """
        mime_message = MIMEText(body, "plain", "utf-8")
        mime_message["To"] = to
        mime_message["Subject"] = subject
        mime_message["In-Reply-To"] = in_reply_to
        mime_message["References"] = references

        raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")

        url = f"{GMAIL_API_BASE_URL}/messages/send"
        request_body = {
            "raw": raw,
            "threadId": thread_id,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self.headers,
                json=request_body,
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(
                    f"Gmail send API error: {response.status_code} - {response.text}"
                )
                raise GmailApiError(
                    f"Failed to send message: {response.text}",
                    status_code=response.status_code,
                )

            return cast(dict[str, Any], response.json())

    async def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: str,
        in_reply_to: str,
        references: str,
    ) -> dict[str, Any]:
        """Create a draft reply email via Gmail API.

        Constructs a MIME message with reply headers and saves it
        as a draft using Gmail API drafts.create endpoint.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            thread_id: Gmail thread ID to reply in
            in_reply_to: Message-ID of the original email
            references: References header value

        Returns:
            Gmail API draft response (id, message)

        Raises:
            GmailApiError: If API call fails
        """
        mime_message = MIMEText(body, "plain", "utf-8")
        mime_message["To"] = to
        mime_message["Subject"] = subject
        mime_message["In-Reply-To"] = in_reply_to
        mime_message["References"] = references

        raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode("utf-8")

        url = f"{GMAIL_API_BASE_URL}/drafts"
        request_body = {
            "message": {
                "raw": raw,
                "threadId": thread_id,
            },
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers=self.headers,
                json=request_body,
                timeout=30.0,
            )

            if response.status_code != 200:
                logger.error(
                    f"Gmail draft API error: {response.status_code} - {response.text}"
                )
                raise GmailApiError(
                    f"Failed to create draft: {response.text}",
                    status_code=response.status_code,
                )

            return cast(dict[str, Any], response.json())
