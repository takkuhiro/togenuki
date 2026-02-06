"""Tests for Learning Service.

Tests for the learning service that orchestrates:
- Fetching past emails from Gmail API
- Analyzing patterns using Gemini API
- Saving results to contact_context
- Updating learning status
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from result import Err, Ok
from uuid6 import uuid7

from src.models import Contact, ContactContext, User
from src.services.gemini_service import GeminiError


def _make_oauth_mock(access_token: str = "access-token-xxx") -> MagicMock:
    """Create a mock GmailOAuthService that returns a valid token."""
    mock_oauth = MagicMock()
    mock_oauth.ensure_valid_access_token = AsyncMock(return_value={
        "access_token": access_token,
        "expires_at": datetime.now(timezone.utc),
    })
    return mock_oauth


class TestProcessLearning:
    """Tests for process_learning function."""

    @pytest.fixture
    def mock_user(self) -> User:
        """Create a mock user with Gmail OAuth tokens."""
        return User(
            id=uuid7(),
            firebase_uid="test-uid-123",
            email="user@example.com",
            gmail_refresh_token="refresh-token-xxx",
            gmail_access_token="access-token-xxx",
            gmail_token_expires_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def mock_contact(self, mock_user: User) -> Contact:
        """Create a mock contact."""
        return Contact(
            id=uuid7(),
            user_id=mock_user.id,
            contact_email="boss@example.com",
            contact_name="上司さん",
            gmail_query="from:boss@example.com",
            is_learning_complete=False,
        )

    @pytest.mark.asyncio
    async def test_process_learning_fetches_emails_via_gmail_api(
        self, mock_user: User, mock_contact: Contact
    ):
        """process_learning should fetch emails using Gmail API."""
        from src.services.learning_service import LearningService

        mock_session = AsyncMock()

        # Mock repository calls
        with (
            patch("src.services.learning_service.get_user_by_id") as mock_get_user,
            patch("src.services.learning_service.get_contact_by_id") as mock_get_contact,
            patch("src.services.learning_service.GmailApiClient") as mock_gmail_class,
            patch("src.services.learning_service.GeminiService") as mock_gemini_class,
            patch("src.services.learning_service.create_contact_context"),
            patch("src.services.learning_service.update_contact_learning_status"),
            patch("src.services.learning_service.get_db") as mock_get_db,
            patch("src.services.learning_service.GmailOAuthService") as mock_oauth_class,
        ):
            mock_get_user.return_value = mock_user
            mock_get_contact.return_value = mock_contact
            mock_get_db.return_value.__aiter__.return_value = iter([mock_session])

            mock_oauth_class.return_value = _make_oauth_mock()

            # Mock Gmail API
            mock_gmail = MagicMock()
            mock_gmail.search_messages = AsyncMock(return_value=[
                {"id": "msg-1", "threadId": "thread-1"},
                {"id": "msg-2", "threadId": "thread-2"},
            ])
            mock_gmail.fetch_message = AsyncMock(return_value={
                "id": "msg-1",
                "payload": {
                    "headers": [{"name": "From", "value": "boss@example.com"}],
                    "mimeType": "text/plain",
                    "body": {"data": "dGVzdA=="},  # base64 "test"
                },
                "internalDate": "1704067200000",
            })
            mock_gmail_class.return_value = mock_gmail

            # Mock Gemini API
            mock_gemini = MagicMock()
            mock_gemini.analyze_patterns = AsyncMock(return_value=Ok('{"contactCharacteristics": {}}'))
            mock_gemini_class.return_value = mock_gemini

            service = LearningService()
            await service.process_learning(mock_contact.id, mock_user.id)

            mock_gmail.search_messages.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_learning_calls_gemini_analyze_patterns(
        self, mock_user: User, mock_contact: Contact
    ):
        """process_learning should call Gemini to analyze patterns."""
        from src.services.learning_service import LearningService

        mock_session = AsyncMock()

        with (
            patch("src.services.learning_service.get_user_by_id") as mock_get_user,
            patch("src.services.learning_service.get_contact_by_id") as mock_get_contact,
            patch("src.services.learning_service.GmailApiClient") as mock_gmail_class,
            patch("src.services.learning_service.GeminiService") as mock_gemini_class,
            patch("src.services.learning_service.create_contact_context"),
            patch("src.services.learning_service.update_contact_learning_status"),
            patch("src.services.learning_service.get_db") as mock_get_db,
            patch("src.services.learning_service.GmailOAuthService") as mock_oauth_class,
        ):
            mock_get_user.return_value = mock_user
            mock_get_contact.return_value = mock_contact
            mock_get_db.return_value.__aiter__.return_value = iter([mock_session])

            mock_oauth_class.return_value = _make_oauth_mock()

            mock_gmail = MagicMock()
            mock_gmail.search_messages = AsyncMock(return_value=[{"id": "msg-1"}])
            mock_gmail.fetch_message = AsyncMock(return_value={
                "id": "msg-1",
                "payload": {
                    "headers": [{"name": "From", "value": "boss@example.com"}],
                    "mimeType": "text/plain",
                    "body": {"data": "dGVzdA=="},
                },
                "internalDate": "1704067200000",
            })
            mock_gmail_class.return_value = mock_gmail

            mock_gemini = MagicMock()
            mock_gemini.analyze_patterns = AsyncMock(return_value=Ok('{"contactCharacteristics": {}}'))
            mock_gemini_class.return_value = mock_gemini

            service = LearningService()
            await service.process_learning(mock_contact.id, mock_user.id)

            mock_gemini.analyze_patterns.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_learning_saves_contact_context(
        self, mock_user: User, mock_contact: Contact
    ):
        """process_learning should save learned patterns to contact_context."""
        from src.services.learning_service import LearningService

        mock_session = AsyncMock()
        learned_patterns = '{"contactCharacteristics": {"tone": "formal"}}'

        with (
            patch("src.services.learning_service.get_user_by_id") as mock_get_user,
            patch("src.services.learning_service.get_contact_by_id") as mock_get_contact,
            patch("src.services.learning_service.GmailApiClient") as mock_gmail_class,
            patch("src.services.learning_service.GeminiService") as mock_gemini_class,
            patch("src.services.learning_service.create_contact_context") as mock_create_context,
            patch("src.services.learning_service.update_contact_learning_status"),
            patch("src.services.learning_service.get_db") as mock_get_db,
            patch("src.services.learning_service.GmailOAuthService") as mock_oauth_class,
        ):
            mock_get_user.return_value = mock_user
            mock_get_contact.return_value = mock_contact
            mock_get_db.return_value.__aiter__.return_value = iter([mock_session])

            mock_oauth_class.return_value = _make_oauth_mock()

            mock_gmail = MagicMock()
            mock_gmail.search_messages = AsyncMock(return_value=[{"id": "msg-1"}])
            mock_gmail.fetch_message = AsyncMock(return_value={
                "id": "msg-1",
                "payload": {
                    "headers": [{"name": "From", "value": "boss@example.com"}],
                    "mimeType": "text/plain",
                    "body": {"data": "dGVzdA=="},
                },
                "internalDate": "1704067200000",
            })
            mock_gmail_class.return_value = mock_gmail

            mock_gemini = MagicMock()
            mock_gemini.analyze_patterns = AsyncMock(return_value=Ok(learned_patterns))
            mock_gemini_class.return_value = mock_gemini

            service = LearningService()
            await service.process_learning(mock_contact.id, mock_user.id)

            mock_create_context.assert_called_once()
            call_args = mock_create_context.call_args
            assert call_args[1]["contact_id"] == mock_contact.id
            assert call_args[1]["learned_patterns"] == learned_patterns

    @pytest.mark.asyncio
    async def test_process_learning_updates_learning_status_on_success(
        self, mock_user: User, mock_contact: Contact
    ):
        """process_learning should update is_learning_complete=True on success."""
        from src.services.learning_service import LearningService

        mock_session = AsyncMock()

        with (
            patch("src.services.learning_service.get_user_by_id") as mock_get_user,
            patch("src.services.learning_service.get_contact_by_id") as mock_get_contact,
            patch("src.services.learning_service.GmailApiClient") as mock_gmail_class,
            patch("src.services.learning_service.GeminiService") as mock_gemini_class,
            patch("src.services.learning_service.create_contact_context"),
            patch("src.services.learning_service.update_contact_learning_status") as mock_update_status,
            patch("src.services.learning_service.get_db") as mock_get_db,
            patch("src.services.learning_service.GmailOAuthService") as mock_oauth_class,
        ):
            mock_get_user.return_value = mock_user
            mock_get_contact.return_value = mock_contact
            mock_get_db.return_value.__aiter__.return_value = iter([mock_session])

            mock_oauth_class.return_value = _make_oauth_mock()

            mock_gmail = MagicMock()
            mock_gmail.search_messages = AsyncMock(return_value=[{"id": "msg-1"}])
            mock_gmail.fetch_message = AsyncMock(return_value={
                "id": "msg-1",
                "payload": {
                    "headers": [{"name": "From", "value": "boss@example.com"}],
                    "mimeType": "text/plain",
                    "body": {"data": "dGVzdA=="},
                },
                "internalDate": "1704067200000",
            })
            mock_gmail_class.return_value = mock_gmail

            mock_gemini = MagicMock()
            mock_gemini.analyze_patterns = AsyncMock(return_value=Ok('{}'))
            mock_gemini_class.return_value = mock_gemini

            service = LearningService()
            await service.process_learning(mock_contact.id, mock_user.id)

            mock_update_status.assert_called()
            call_args = mock_update_status.call_args
            assert call_args[1]["is_complete"] is True

    @pytest.mark.asyncio
    async def test_process_learning_sets_failed_at_on_gmail_error(
        self, mock_user: User, mock_contact: Contact
    ):
        """process_learning should set learning_failed_at on Gmail API error."""
        from src.services.gmail_service import GmailApiError
        from src.services.learning_service import LearningService

        mock_session = AsyncMock()

        with (
            patch("src.services.learning_service.get_user_by_id") as mock_get_user,
            patch("src.services.learning_service.get_contact_by_id") as mock_get_contact,
            patch("src.services.learning_service.GmailApiClient") as mock_gmail_class,
            patch("src.services.learning_service.update_contact_learning_status") as mock_update_status,
            patch("src.services.learning_service.get_db") as mock_get_db,
            patch("src.services.learning_service.GmailOAuthService") as mock_oauth_class,
        ):
            mock_get_user.return_value = mock_user
            mock_get_contact.return_value = mock_contact
            mock_get_db.return_value.__aiter__.return_value = iter([mock_session])

            mock_oauth_class.return_value = _make_oauth_mock()

            mock_gmail = MagicMock()
            mock_gmail.search_messages = AsyncMock(side_effect=GmailApiError("API Error", 500))
            mock_gmail_class.return_value = mock_gmail

            service = LearningService()
            await service.process_learning(mock_contact.id, mock_user.id)

            mock_update_status.assert_called()
            call_args = mock_update_status.call_args
            assert call_args[1]["is_complete"] is False
            assert call_args[1]["failed_at"] is not None

    @pytest.mark.asyncio
    async def test_process_learning_retries_on_gemini_error(
        self, mock_user: User, mock_contact: Contact
    ):
        """process_learning should retry on Gemini API error (max 3 times)."""
        from src.services.learning_service import LearningService

        mock_session = AsyncMock()

        with (
            patch("src.services.learning_service.get_user_by_id") as mock_get_user,
            patch("src.services.learning_service.get_contact_by_id") as mock_get_contact,
            patch("src.services.learning_service.GmailApiClient") as mock_gmail_class,
            patch("src.services.learning_service.GeminiService") as mock_gemini_class,
            patch("src.services.learning_service.create_contact_context"),
            patch("src.services.learning_service.update_contact_learning_status") as mock_update_status,
            patch("src.services.learning_service.get_db") as mock_get_db,
            patch("src.services.learning_service.GmailOAuthService") as mock_oauth_class,
        ):
            mock_get_user.return_value = mock_user
            mock_get_contact.return_value = mock_contact
            mock_get_db.return_value.__aiter__.return_value = iter([mock_session])

            mock_oauth_class.return_value = _make_oauth_mock()

            mock_gmail = MagicMock()
            mock_gmail.search_messages = AsyncMock(return_value=[{"id": "msg-1"}])
            mock_gmail.fetch_message = AsyncMock(return_value={
                "id": "msg-1",
                "payload": {
                    "headers": [{"name": "From", "value": "boss@example.com"}],
                    "mimeType": "text/plain",
                    "body": {"data": "dGVzdA=="},
                },
                "internalDate": "1704067200000",
            })
            mock_gmail_class.return_value = mock_gmail

            mock_gemini = MagicMock()
            # Fail twice, succeed on third try
            mock_gemini.analyze_patterns = AsyncMock(side_effect=[
                Err(GeminiError.API_ERROR),
                Err(GeminiError.API_ERROR),
                Ok('{"contactCharacteristics": {}}'),
            ])
            mock_gemini_class.return_value = mock_gemini

            service = LearningService()
            await service.process_learning(mock_contact.id, mock_user.id)

            # Should have been called 3 times
            assert mock_gemini.analyze_patterns.call_count == 3
            # Should update status to complete
            call_args = mock_update_status.call_args
            assert call_args[1]["is_complete"] is True

    @pytest.mark.asyncio
    async def test_process_learning_fails_after_max_retries(
        self, mock_user: User, mock_contact: Contact
    ):
        """process_learning should set failed_at after max retries exhausted."""
        from src.services.learning_service import LearningService

        mock_session = AsyncMock()

        with (
            patch("src.services.learning_service.get_user_by_id") as mock_get_user,
            patch("src.services.learning_service.get_contact_by_id") as mock_get_contact,
            patch("src.services.learning_service.GmailApiClient") as mock_gmail_class,
            patch("src.services.learning_service.GeminiService") as mock_gemini_class,
            patch("src.services.learning_service.update_contact_learning_status") as mock_update_status,
            patch("src.services.learning_service.get_db") as mock_get_db,
            patch("src.services.learning_service.GmailOAuthService") as mock_oauth_class,
        ):
            mock_get_user.return_value = mock_user
            mock_get_contact.return_value = mock_contact
            mock_get_db.return_value.__aiter__.return_value = iter([mock_session])

            mock_oauth_class.return_value = _make_oauth_mock()

            mock_gmail = MagicMock()
            mock_gmail.search_messages = AsyncMock(return_value=[{"id": "msg-1"}])
            mock_gmail.fetch_message = AsyncMock(return_value={
                "id": "msg-1",
                "payload": {
                    "headers": [{"name": "From", "value": "boss@example.com"}],
                    "mimeType": "text/plain",
                    "body": {"data": "dGVzdA=="},
                },
                "internalDate": "1704067200000",
            })
            mock_gmail_class.return_value = mock_gmail

            mock_gemini = MagicMock()
            # Always fail
            mock_gemini.analyze_patterns = AsyncMock(return_value=Err(GeminiError.API_ERROR))
            mock_gemini_class.return_value = mock_gemini

            service = LearningService()
            await service.process_learning(mock_contact.id, mock_user.id)

            # Should have been called 3 times (max retries)
            assert mock_gemini.analyze_patterns.call_count == 3
            # Should update status to failed
            call_args = mock_update_status.call_args
            assert call_args[1]["is_complete"] is False
            assert call_args[1]["failed_at"] is not None

    @pytest.mark.asyncio
    async def test_process_learning_refreshes_expired_access_token(
        self, mock_user: User, mock_contact: Contact
    ):
        """process_learning should refresh expired access token before calling Gmail API."""
        from src.services.learning_service import LearningService

        mock_session = AsyncMock()

        with (
            patch("src.services.learning_service.get_user_by_id") as mock_get_user,
            patch("src.services.learning_service.get_contact_by_id") as mock_get_contact,
            patch("src.services.learning_service.GmailApiClient") as mock_gmail_class,
            patch("src.services.learning_service.GeminiService") as mock_gemini_class,
            patch("src.services.learning_service.create_contact_context"),
            patch("src.services.learning_service.update_contact_learning_status"),
            patch("src.services.learning_service.get_db") as mock_get_db,
            patch("src.services.learning_service.GmailOAuthService") as mock_oauth_class,
        ):
            mock_get_user.return_value = mock_user
            mock_get_contact.return_value = mock_contact
            mock_get_db.return_value.__aiter__.return_value = iter([mock_session])

            # Mock OAuth service - token is refreshed to a new value
            mock_oauth = _make_oauth_mock("new-refreshed-token")
            mock_oauth_class.return_value = mock_oauth

            # Mock Gmail API
            mock_gmail = MagicMock()
            mock_gmail.search_messages = AsyncMock(return_value=[{"id": "msg-1"}])
            mock_gmail.fetch_message = AsyncMock(return_value={
                "id": "msg-1",
                "payload": {
                    "headers": [{"name": "From", "value": "boss@example.com"}],
                    "mimeType": "text/plain",
                    "body": {"data": "dGVzdA=="},
                },
                "internalDate": "1704067200000",
            })
            mock_gmail_class.return_value = mock_gmail

            # Mock Gemini API
            mock_gemini = MagicMock()
            mock_gemini.analyze_patterns = AsyncMock(return_value=Ok('{"contactCharacteristics": {}}'))
            mock_gemini_class.return_value = mock_gemini

            service = LearningService()
            await service.process_learning(mock_contact.id, mock_user.id)

            # Should call ensure_valid_access_token with original token values
            mock_oauth.ensure_valid_access_token.assert_called_once()
            call_args = mock_oauth.ensure_valid_access_token.call_args
            assert call_args[1]["current_token"] == "access-token-xxx"
            assert call_args[1]["refresh_token"] == "refresh-token-xxx"

            # Gmail client should be created with refreshed token
            mock_gmail_class.assert_called_once_with("new-refreshed-token")

    @pytest.mark.asyncio
    async def test_process_learning_fails_when_token_refresh_fails(
        self, mock_user: User, mock_contact: Contact
    ):
        """process_learning should set learning_failed_at when token refresh fails."""
        from src.services.learning_service import LearningService

        mock_session = AsyncMock()

        with (
            patch("src.services.learning_service.get_user_by_id") as mock_get_user,
            patch("src.services.learning_service.get_contact_by_id") as mock_get_contact,
            patch("src.services.learning_service.GmailApiClient") as mock_gmail_class,
            patch("src.services.learning_service.update_contact_learning_status") as mock_update_status,
            patch("src.services.learning_service.get_db") as mock_get_db,
            patch("src.services.learning_service.GmailOAuthService") as mock_oauth_class,
        ):
            mock_get_user.return_value = mock_user
            mock_get_contact.return_value = mock_contact
            mock_get_db.return_value.__aiter__.return_value = iter([mock_session])

            # Mock OAuth service - refresh fails
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(return_value=None)
            mock_oauth_class.return_value = mock_oauth

            mock_gmail = MagicMock()
            mock_gmail_class.return_value = mock_gmail

            service = LearningService()
            await service.process_learning(mock_contact.id, mock_user.id)

            # Gmail should not be called
            mock_gmail.search_messages.assert_not_called()

            # Should mark as failed
            mock_update_status.assert_called()
            call_args = mock_update_status.call_args
            assert call_args[1]["is_complete"] is False
            assert call_args[1]["failed_at"] is not None

    @pytest.mark.asyncio
    async def test_process_learning_skips_when_user_not_found(
        self, mock_contact: Contact
    ):
        """process_learning should skip when user is not found."""
        from src.services.learning_service import LearningService

        mock_session = AsyncMock()

        with (
            patch("src.services.learning_service.get_user_by_id") as mock_get_user,
            patch("src.services.learning_service.get_contact_by_id") as mock_get_contact,
            patch("src.services.learning_service.GmailApiClient") as mock_gmail_class,
            patch("src.services.learning_service.get_db") as mock_get_db,
        ):
            mock_get_user.return_value = None  # User not found
            mock_get_contact.return_value = mock_contact
            mock_get_db.return_value.__aiter__.return_value = iter([mock_session])

            mock_gmail = MagicMock()
            mock_gmail_class.return_value = mock_gmail

            service = LearningService()
            await service.process_learning(mock_contact.id, uuid7())

            # Gmail should not be called
            mock_gmail.search_messages.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_learning_skips_when_contact_not_found(
        self, mock_user: User
    ):
        """process_learning should skip when contact is not found."""
        from src.services.learning_service import LearningService

        mock_session = AsyncMock()

        with (
            patch("src.services.learning_service.get_user_by_id") as mock_get_user,
            patch("src.services.learning_service.get_contact_by_id") as mock_get_contact,
            patch("src.services.learning_service.GmailApiClient") as mock_gmail_class,
            patch("src.services.learning_service.get_db") as mock_get_db,
        ):
            mock_get_user.return_value = mock_user
            mock_get_contact.return_value = None  # Contact not found
            mock_get_db.return_value.__aiter__.return_value = iter([mock_session])

            mock_gmail = MagicMock()
            mock_gmail_class.return_value = mock_gmail

            service = LearningService()
            await service.process_learning(uuid7(), mock_user.id)

            # Gmail should not be called
            mock_gmail.search_messages.assert_not_called()
