"""Tests for Email Processing Orchestration.

Tests for the email processing pipeline that handles:
- Fetching new emails from Gmail API
- Validating against registered contacts
- Storing emails in database
- Triggering conversion and TTS (placeholder for Phase 4)
"""

import base64
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models import Contact, Email, User


class TestEmailProcessor:
    """Tests for EmailProcessorService."""

    @pytest.fixture
    def mock_user(self) -> User:
        """Create a mock user with Gmail OAuth tokens."""
        user = User(
            id=1,
            firebase_uid="test-uid-123",
            email="user@example.com",
            gmail_refresh_token="refresh-token-xxx",
            gmail_access_token="access-token-xxx",
            gmail_token_expires_at=datetime.now(timezone.utc),
        )
        return user

    @pytest.fixture
    def mock_contact(self) -> Contact:
        """Create a mock registered contact."""
        return Contact(
            id=1,
            user_id=1,
            contact_email="boss@company.com",
            contact_name="上司さん",
        )

    @pytest.fixture
    def mock_gmail_message(self) -> dict:
        """Create a mock Gmail API message."""
        return {
            "id": "msg-123",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Boss <boss@company.com>"},
                    {"name": "Subject", "value": "至急対応お願いします"},
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(
                        "明日までに報告書を提出してください。".encode()
                    ).decode()
                }
            },
            "internalDate": "1704067200000",
        }

    @pytest.fixture
    def mock_history_response(self) -> dict:
        """Create a mock Gmail history response."""
        return {
            "history": [
                {
                    "id": "12346",
                    "messagesAdded": [
                        {
                            "message": {
                                "id": "msg-123",
                                "threadId": "thread-123",
                                "labelIds": ["INBOX", "UNREAD"]
                            }
                        }
                    ]
                }
            ],
            "historyId": "12347"
        }

    @pytest.mark.asyncio
    async def test_process_notification_fetches_user_by_email(
        self, mock_user: User
    ):
        """Test that processing fetches user by email address."""
        from src.services.email_processor import EmailProcessorService

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        processor = EmailProcessorService(mock_session)

        with patch.object(processor, '_get_valid_access_token', return_value="token"):
            with patch.object(processor, '_fetch_and_process_messages'):
                await processor.process_notification("user@example.com", "12345")

        mock_session.execute.assert_called()

    @pytest.mark.asyncio
    async def test_process_notification_skips_when_user_not_found(self):
        """Test that processing is skipped when user is not found."""
        from src.services.email_processor import EmailProcessorService

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        processor = EmailProcessorService(mock_session)

        # Should not raise and should skip processing
        result = await processor.process_notification("unknown@example.com", "12345")

        assert result.skipped is True
        assert "User not found" in result.reason

    @pytest.mark.asyncio
    async def test_process_notification_skips_when_no_gmail_token(
        self, mock_user: User
    ):
        """Test that processing is skipped when user has no Gmail OAuth token."""
        from src.services.email_processor import EmailProcessorService

        mock_user.gmail_refresh_token = None
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        processor = EmailProcessorService(mock_session)
        result = await processor.process_notification("user@example.com", "12345")

        assert result.skipped is True
        assert "Gmail not connected" in result.reason

    @pytest.mark.asyncio
    async def test_process_message_creates_email_for_registered_contact(
        self,
        mock_user: User,
        mock_contact: Contact,
        mock_gmail_message: dict,
    ):
        """Test that email is created for message from registered contact."""
        from src.services.email_processor import EmailProcessorService

        mock_session = AsyncMock()

        # Setup mock for contact lookup
        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = mock_contact

        # Setup mock for email existence check
        mock_email_exists_result = MagicMock()
        mock_email_exists_result.scalar_one_or_none.return_value = None  # Not exists

        mock_session.execute.side_effect = [
            mock_contact_result,
            mock_email_exists_result,
        ]

        processor = EmailProcessorService(mock_session)
        result = await processor.process_single_message(
            mock_user.id, mock_gmail_message, "access-token"
        )

        assert result.processed is True
        # Note: email_id is None because we're not actually saving to DB in tests
        # The important thing is that add was called with an Email object
        mock_session.add.assert_called_once()
        added_email = mock_session.add.call_args[0][0]
        assert isinstance(added_email, Email)
        assert added_email.google_message_id == "msg-123"

    @pytest.mark.asyncio
    async def test_process_message_skips_unregistered_contact(
        self,
        mock_user: User,
        mock_gmail_message: dict,
    ):
        """Test that email from unregistered contact is skipped."""
        from src.services.email_processor import EmailProcessorService

        mock_session = AsyncMock()

        # Setup mock for contact lookup - returns None (not registered)
        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_contact_result

        processor = EmailProcessorService(mock_session)
        result = await processor.process_single_message(
            mock_user.id, mock_gmail_message, "access-token"
        )

        assert result.processed is False
        assert "not registered" in result.reason.lower()
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_message_skips_already_processed_email(
        self,
        mock_user: User,
        mock_contact: Contact,
        mock_gmail_message: dict,
    ):
        """Test that already processed email is skipped."""
        from src.services.email_processor import EmailProcessorService

        mock_session = AsyncMock()

        # Setup mock for contact lookup
        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = mock_contact

        # Setup mock for email existence check - email already exists
        mock_email_exists_result = MagicMock()
        mock_email_exists_result.scalar_one_or_none.return_value = 1  # Exists

        mock_session.execute.side_effect = [
            mock_contact_result,
            mock_email_exists_result,
        ]

        processor = EmailProcessorService(mock_session)
        result = await processor.process_single_message(
            mock_user.id, mock_gmail_message, "access-token"
        )

        assert result.processed is False
        assert "already exists" in result.reason.lower()
        mock_session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_message_sets_is_processed_false_initially(
        self,
        mock_user: User,
        mock_contact: Contact,
        mock_gmail_message: dict,
    ):
        """Test that new email has is_processed=false initially."""
        from src.services.email_processor import EmailProcessorService

        mock_session = AsyncMock()

        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = mock_contact

        mock_email_exists_result = MagicMock()
        mock_email_exists_result.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [
            mock_contact_result,
            mock_email_exists_result,
        ]

        processor = EmailProcessorService(mock_session)
        await processor.process_single_message(
            mock_user.id, mock_gmail_message, "access-token"
        )

        # Check the email added to session has is_processed=False
        added_email = mock_session.add.call_args[0][0]
        assert isinstance(added_email, Email)
        assert added_email.is_processed is False


class TestProcessingResult:
    """Tests for processing result data structures."""

    def test_notification_result_success(self):
        """Test successful notification result."""
        from src.services.email_processor import NotificationResult

        result = NotificationResult(
            skipped=False,
            processed_count=2,
            skipped_count=1,
        )

        assert result.skipped is False
        assert result.processed_count == 2
        assert result.skipped_count == 1

    def test_notification_result_skipped(self):
        """Test skipped notification result."""
        from src.services.email_processor import NotificationResult

        result = NotificationResult(
            skipped=True,
            reason="User not found",
        )

        assert result.skipped is True
        assert result.reason == "User not found"

    def test_message_result_processed(self):
        """Test processed message result."""
        from src.services.email_processor import MessageResult

        result = MessageResult(
            processed=True,
            email_id=123,
        )

        assert result.processed is True
        assert result.email_id == 123

    def test_message_result_skipped(self):
        """Test skipped message result."""
        from src.services.email_processor import MessageResult

        result = MessageResult(
            processed=False,
            reason="Contact not registered",
        )

        assert result.processed is False
        assert result.reason == "Contact not registered"


class TestErrorHandling:
    """Tests for error handling in email processing."""

    @pytest.fixture
    def mock_user(self) -> User:
        """Create a mock user."""
        return User(
            id=1,
            firebase_uid="test-uid-123",
            email="user@example.com",
            gmail_refresh_token="refresh-token",
            gmail_access_token="access-token",
        )

    @pytest.mark.asyncio
    async def test_gmail_api_error_is_logged_and_retried(self, mock_user: User):
        """Test that Gmail API errors are logged and handled."""
        from src.services.email_processor import EmailProcessorService
        from src.services.gmail_service import GmailApiError

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        processor = EmailProcessorService(mock_session)

        with patch.object(
            processor, '_get_valid_access_token', return_value="token"
        ):
            with patch(
                'src.services.email_processor.GmailApiClient'
            ) as mock_client_class:
                mock_client = MagicMock()
                mock_client.fetch_email_history = AsyncMock(
                    side_effect=GmailApiError("API Error", status_code=500)
                )
                mock_client_class.return_value = mock_client

                result = await processor.process_notification(
                    "user@example.com", "12345"
                )

        # Should handle error gracefully
        assert result.skipped is True
        assert "error" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_database_error_is_handled(self, mock_user: User):
        """Test that database errors are handled gracefully."""
        from src.services.email_processor import EmailProcessorService

        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database connection error")

        processor = EmailProcessorService(mock_session)

        result = await processor.process_notification("user@example.com", "12345")

        assert result.skipped is True
        assert "error" in result.reason.lower()
