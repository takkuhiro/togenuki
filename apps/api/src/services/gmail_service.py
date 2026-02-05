"""Gmail API Service.

Provides functionality to:
- Fetch email content from Gmail API
- Extract sender information and email body
- Validate against registered contacts
- Store emails in database
"""

import base64
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Contact, Email
from src.utils.logging import get_logger

logger = get_logger(__name__)

GMAIL_API_BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailApiError(Exception):
    """Exception raised when Gmail API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


def extract_sender_info(from_header: str) -> tuple[Optional[str], str]:
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
    match = re.match(r'^(.+?)\s*<([^>]+)>$', from_header.strip())
    if match:
        name = match.group(1).strip().strip('"')
        email = match.group(2).strip()
        return name, email

    # Pattern: just "email@domain.com"
    return None, from_header.strip()


def get_header_value(headers: list[dict], name: str) -> Optional[str]:
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
        "sender_email": sender_email,
        "sender_name": sender_name,
        "subject": get_header_value(headers, "Subject"),
        "original_body": extract_email_body(payload),
        "received_at": received_at,
    }


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
    ) -> dict:
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
                    status_code=response.status_code
                )

            return response.json()

    async def list_recent_messages(
        self, max_results: int = 10, label_ids: list[str] | None = None
    ) -> list[dict]:
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
        params = {
            "maxResults": max_results,
            "labelIds": label_ids,
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, headers=self.headers, params=params, timeout=30.0
            )

            if response.status_code != 200:
                logger.error(
                    f"Gmail messages.list API error: {response.status_code} - {response.text}"
                )
                raise GmailApiError(
                    f"Failed to list messages: {response.text}",
                    status_code=response.status_code
                )

            data = response.json()
            return data.get("messages", [])

    async def fetch_message(self, message_id: str) -> dict:
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
                    status_code=response.status_code
                )

            return response.json()


async def is_registered_contact(
    session: AsyncSession, user_id: int, sender_email: str
) -> bool:
    """Check if sender is a registered contact for the user.

    Args:
        session: Database session
        user_id: The user's ID
        sender_email: The sender's email address

    Returns:
        True if sender is registered, False otherwise
    """
    contact = await get_contact_for_email(session, user_id, sender_email)
    return contact is not None


async def get_contact_for_email(
    session: AsyncSession, user_id: int, sender_email: str
) -> Optional[Contact]:
    """Get contact record for a sender email.

    Args:
        session: Database session
        user_id: The user's ID
        sender_email: The sender's email address

    Returns:
        Contact if found, None otherwise
    """
    query = select(Contact).where(
        Contact.user_id == user_id,
        Contact.contact_email == sender_email
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def email_exists(session: AsyncSession, google_message_id: str) -> bool:
    """Check if an email already exists in the database.

    Args:
        session: Database session
        google_message_id: The Gmail message ID

    Returns:
        True if email exists, False otherwise
    """
    query = select(Email.id).where(Email.google_message_id == google_message_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


async def create_email_record(
    session: AsyncSession,
    user_id: int,
    contact_id: Optional[int],
    email_data: dict,
) -> Email:
    """Create a new email record in the database.

    Args:
        session: Database session
        user_id: The user's ID
        contact_id: The contact's ID (if registered)
        email_data: Parsed email data dict

    Returns:
        Created Email model instance
    """
    email = Email(
        user_id=user_id,
        contact_id=contact_id,
        google_message_id=email_data["google_message_id"],
        sender_email=email_data["sender_email"],
        sender_name=email_data.get("sender_name"),
        subject=email_data.get("subject"),
        original_body=email_data.get("original_body"),
        received_at=email_data.get("received_at"),
        is_processed=False,
    )
    session.add(email)
    return email
