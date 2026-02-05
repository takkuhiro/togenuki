"""Tests for Gmail API Service.

Tests for fetching email content from Gmail API, extracting sender information,
and validating registered contacts.
"""

import base64
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Contact, Email, User


class TestGmailService:
    """Tests for Gmail API integration service."""

    @pytest.fixture
    def mock_gmail_message(self) -> dict:
        """Create a mock Gmail API message response."""
        return {
            "id": "18d1234567890abc",
            "threadId": "18d1234567890abc",
            "labelIds": ["INBOX", "UNREAD"],
            "snippet": "This is a test email...",
            "internalDate": "1704067200000",  # 2024-01-01 00:00:00 UTC
            "payload": {
                "headers": [
                    {"name": "From", "value": "Boss <boss@company.com>"},
                    {"name": "To", "value": "user@example.com"},
                    {"name": "Subject", "value": "至急！レポート提出について"},
                    {"name": "Date", "value": "Mon, 1 Jan 2024 00:00:00 +0000"},
                ],
                "mimeType": "text/plain",
                "body": {
                    "size": 100,
                    "data": base64.urlsafe_b64encode(
                        "本日中にレポートを提出してください。".encode()
                    ).decode()
                }
            }
        }

    @pytest.fixture
    def mock_multipart_message(self) -> dict:
        """Create a mock Gmail API multipart message response."""
        return {
            "id": "18d1234567890def",
            "threadId": "18d1234567890def",
            "labelIds": ["INBOX"],
            "snippet": "This is a multipart email...",
            "internalDate": "1704067200000",
            "payload": {
                "headers": [
                    {"name": "From", "value": "partner@external.com"},
                    {"name": "To", "value": "user@example.com"},
                    {"name": "Subject", "value": "Meeting Request"},
                ],
                "mimeType": "multipart/alternative",
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {
                            "size": 50,
                            "data": base64.urlsafe_b64encode(
                                "Please attend the meeting tomorrow.".encode()
                            ).decode()
                        }
                    },
                    {
                        "mimeType": "text/html",
                        "body": {
                            "size": 100,
                            "data": base64.urlsafe_b64encode(
                                "<p>Please attend the meeting tomorrow.</p>".encode()
                            ).decode()
                        }
                    }
                ]
            }
        }

    @pytest.mark.asyncio
    async def test_extract_sender_info_from_header(self):
        """Test extracting sender name and email from From header."""
        from src.services.gmail_service import extract_sender_info

        # Test "Name <email@domain.com>" format
        name, email = extract_sender_info("Boss <boss@company.com>")
        assert name == "Boss"
        assert email == "boss@company.com"

        # Test "email@domain.com" only format
        name, email = extract_sender_info("someone@example.com")
        assert name is None
        assert email == "someone@example.com"

        # Test "Name Name <email@domain.com>" format with spaces
        name, email = extract_sender_info("John Doe <john.doe@example.com>")
        assert name == "John Doe"
        assert email == "john.doe@example.com"

    @pytest.mark.asyncio
    async def test_extract_email_body_plain_text(self, mock_gmail_message: dict):
        """Test extracting body from plain text email."""
        from src.services.gmail_service import extract_email_body

        body = extract_email_body(mock_gmail_message["payload"])
        assert body == "本日中にレポートを提出してください。"

    @pytest.mark.asyncio
    async def test_extract_email_body_multipart(self, mock_multipart_message: dict):
        """Test extracting body from multipart email (prefers text/plain)."""
        from src.services.gmail_service import extract_email_body

        body = extract_email_body(mock_multipart_message["payload"])
        assert body == "Please attend the meeting tomorrow."

    @pytest.mark.asyncio
    async def test_parse_gmail_message(self, mock_gmail_message: dict):
        """Test parsing a complete Gmail message."""
        from src.services.gmail_service import parse_gmail_message

        result = parse_gmail_message(mock_gmail_message)

        assert result["google_message_id"] == "18d1234567890abc"
        assert result["sender_email"] == "boss@company.com"
        assert result["sender_name"] == "Boss"
        assert result["subject"] == "至急！レポート提出について"
        assert result["original_body"] == "本日中にレポートを提出してください。"
        assert result["received_at"] is not None

    @pytest.mark.asyncio
    async def test_get_header_value(self, mock_gmail_message: dict):
        """Test extracting specific header values."""
        from src.services.gmail_service import get_header_value

        headers = mock_gmail_message["payload"]["headers"]

        assert get_header_value(headers, "From") == "Boss <boss@company.com>"
        assert get_header_value(headers, "Subject") == "至急！レポート提出について"
        assert get_header_value(headers, "X-Custom") is None


class TestContactValidation:
    """Tests for validating sender against registered contacts."""

    @pytest.fixture
    def mock_user(self) -> User:
        """Create a mock user."""
        user = User(
            id=1,
            firebase_uid="test-uid-123",
            email="user@example.com",
        )
        return user

    @pytest.fixture
    def mock_contact(self) -> Contact:
        """Create a mock registered contact."""
        contact = Contact(
            id=1,
            user_id=1,
            contact_email="boss@company.com",
            contact_name="上司さん",
        )
        return contact

    @pytest.mark.asyncio
    async def test_is_registered_contact_returns_true_for_registered(
        self, mock_user: User, mock_contact: Contact
    ):
        """Test that registered contact returns True."""
        from src.services.gmail_service import is_registered_contact

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_contact
        mock_session.execute.return_value = mock_result

        result = await is_registered_contact(
            mock_session, mock_user.id, "boss@company.com"
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_is_registered_contact_returns_false_for_unregistered(
        self, mock_user: User
    ):
        """Test that unregistered contact returns False."""
        from src.services.gmail_service import is_registered_contact

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await is_registered_contact(
            mock_session, mock_user.id, "unknown@example.com"
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_get_contact_for_email_returns_contact_when_exists(
        self, mock_user: User, mock_contact: Contact
    ):
        """Test getting contact by email when it exists."""
        from src.services.gmail_service import get_contact_for_email

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_contact
        mock_session.execute.return_value = mock_result

        result = await get_contact_for_email(
            mock_session, mock_user.id, "boss@company.com"
        )

        assert result is not None
        assert result.contact_email == "boss@company.com"

    @pytest.mark.asyncio
    async def test_get_contact_for_email_returns_none_when_not_exists(
        self, mock_user: User
    ):
        """Test getting contact by email when it doesn't exist."""
        from src.services.gmail_service import get_contact_for_email

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await get_contact_for_email(
            mock_session, mock_user.id, "unknown@example.com"
        )

        assert result is None


class TestGmailApiClient:
    """Tests for Gmail API HTTP client operations."""

    @pytest.fixture
    def mock_http_response(self) -> dict:
        """Create a mock Gmail API history response."""
        return {
            "history": [
                {
                    "id": "12346",
                    "messagesAdded": [
                        {
                            "message": {
                                "id": "18d1234567890abc",
                                "threadId": "18d1234567890abc",
                                "labelIds": ["INBOX", "UNREAD"]
                            }
                        }
                    ]
                }
            ],
            "historyId": "12347"
        }

    @pytest.mark.asyncio
    async def test_fetch_email_history_makes_correct_api_call(
        self, mock_http_response: dict
    ):
        """Test that fetchEmailHistory calls Gmail API correctly."""
        from src.services.gmail_service import GmailApiClient

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_http_response
            mock_client.get.return_value = mock_response

            client = GmailApiClient("test-access-token")
            result = await client.fetch_email_history("12345")

        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert "history" in call_args[0][0]
        assert call_args[1]["params"]["startHistoryId"] == "12345"

    @pytest.mark.asyncio
    async def test_fetch_message_returns_parsed_message(self):
        """Test that fetchMessage returns message details."""
        from src.services.gmail_service import GmailApiClient

        mock_message = {
            "id": "18d1234567890abc",
            "payload": {
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Subject", "value": "Test Subject"},
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(b"Test body").decode()
                }
            },
            "internalDate": "1704067200000"
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_message
            mock_client.get.return_value = mock_response

            client = GmailApiClient("test-access-token")
            result = await client.fetch_message("18d1234567890abc")

        assert result is not None
        assert result["id"] == "18d1234567890abc"

    @pytest.mark.asyncio
    async def test_fetch_message_handles_api_error(self):
        """Test that fetchMessage handles API errors gracefully."""
        from src.services.gmail_service import GmailApiClient, GmailApiError

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
            mock_client.get.return_value = mock_response

            client = GmailApiClient("invalid-token")

            with pytest.raises(GmailApiError):
                await client.fetch_message("18d1234567890abc")


class TestEmailStorage:
    """Tests for storing emails in database."""

    @pytest.mark.asyncio
    async def test_create_email_record(self):
        """Test creating a new email record in database."""
        from src.services.gmail_service import create_email_record

        mock_session = AsyncMock(spec=AsyncSession)

        email_data = {
            "google_message_id": "18d1234567890abc",
            "sender_email": "boss@company.com",
            "sender_name": "Boss",
            "subject": "Test Subject",
            "original_body": "Test body content",
            "received_at": datetime.now(timezone.utc),
        }

        await create_email_record(
            session=mock_session,
            user_id=1,
            contact_id=1,
            email_data=email_data,
        )

        mock_session.add.assert_called_once()
        added_email = mock_session.add.call_args[0][0]
        assert isinstance(added_email, Email)
        assert added_email.google_message_id == "18d1234567890abc"
        assert added_email.is_processed is False

    @pytest.mark.asyncio
    async def test_email_exists_returns_true_when_exists(self):
        """Test checking if email already exists in database."""
        from src.services.gmail_service import email_exists

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 1  # Email exists
        mock_session.execute.return_value = mock_result

        result = await email_exists(mock_session, "18d1234567890abc")

        assert result is True

    @pytest.mark.asyncio
    async def test_email_exists_returns_false_when_not_exists(self):
        """Test checking if email doesn't exist in database."""
        from src.services.gmail_service import email_exists

        mock_session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await email_exists(mock_session, "nonexistent-id")

        assert result is False
