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
from uuid6 import uuid7

from src.models import Contact, Email, User


class TestEmailProcessor:
    """Tests for EmailProcessorService."""

    @pytest.fixture
    def mock_user(self) -> User:
        """Create a mock user with Gmail OAuth tokens."""
        user = User(
            id=uuid7(),
            firebase_uid="test-uid-123",
            email="user@example.com",
            gmail_refresh_token="refresh-token-xxx",
            gmail_access_token="access-token-xxx",
            gmail_token_expires_at=datetime.now(timezone.utc),
            gmail_history_id="12345",
        )
        return user

    @pytest.fixture
    def mock_contact(self, mock_user: User) -> Contact:
        """Create a mock registered contact."""
        return Contact(
            id=uuid7(),
            user_id=mock_user.id,
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
                },
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
                                "labelIds": ["INBOX", "UNREAD"],
                            }
                        }
                    ],
                }
            ],
            "historyId": "12347",
        }

    @pytest.mark.asyncio
    async def test_process_notification_fetches_user_by_email(self, mock_user: User):
        """Test that processing fetches user by email address."""
        from src.services.email_processor import EmailProcessorService

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute.return_value = mock_result

        processor = EmailProcessorService(mock_session)

        with (
            patch.object(processor, "_get_valid_access_token", return_value="token"),
            patch.object(processor, "_fetch_and_process_messages"),
        ):
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
        from result import Ok

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

        with (
            patch("src.services.email_processor.GeminiService") as mock_gemini_class,
            patch("src.services.email_processor.TTSService") as mock_tts_class,
        ):
            mock_gemini = MagicMock()
            mock_gemini.convert_email = AsyncMock(return_value=Ok("変換済みテキスト"))
            mock_gemini_class.return_value = mock_gemini

            mock_tts = MagicMock()
            mock_tts.synthesize_and_upload = AsyncMock(
                return_value=Ok("audio/email123_20240115.wav")
            )
            mock_tts_class.return_value = mock_tts

            processor = EmailProcessorService(mock_session)
            result = await processor._process_single_message(
                mock_user.id, mock_gmail_message
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
        result = await processor._process_single_message(
            mock_user.id, mock_gmail_message
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
        result = await processor._process_single_message(
            mock_user.id, mock_gmail_message
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
        from result import Err

        from src.services.email_processor import EmailProcessorService
        from src.services.gemini_service import GeminiError

        mock_session = AsyncMock()

        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = mock_contact

        mock_email_exists_result = MagicMock()
        mock_email_exists_result.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [
            mock_contact_result,
            mock_email_exists_result,
        ]

        with (
            patch("src.services.email_processor.GeminiService") as mock_gemini_class,
            patch("src.services.email_processor.TTSService") as mock_tts_class,
        ):
            # Gemini fails so is_processed stays False
            mock_gemini = MagicMock()
            mock_gemini.convert_email = AsyncMock(
                return_value=Err(GeminiError.API_ERROR)
            )
            mock_gemini_class.return_value = mock_gemini

            mock_tts = MagicMock()
            mock_tts_class.return_value = mock_tts

            processor = EmailProcessorService(mock_session)
            await processor._process_single_message(mock_user.id, mock_gmail_message)

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

        test_email_id = uuid7()
        result = MessageResult(
            processed=True,
            email_id=test_email_id,
        )

        assert result.processed is True
        assert result.email_id == test_email_id

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
            id=uuid7(),
            firebase_uid="test-uid-123",
            email="user@example.com",
            gmail_refresh_token="refresh-token",
            gmail_access_token="access-token",
            gmail_history_id="12345",
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

        with (
            patch.object(processor, "_get_valid_access_token", return_value="token"),
            patch("src.services.email_processor.GmailApiClient") as mock_client_class,
        ):
            mock_client = MagicMock()
            mock_client.fetch_email_history = AsyncMock(
                side_effect=GmailApiError("API Error", status_code=500)
            )
            mock_client_class.return_value = mock_client

            # Use historyId greater than stored (12345) to pass the skip check
            result = await processor.process_notification("user@example.com", "99999")

        # Should handle error gracefully
        assert result.skipped is True
        assert result.reason is not None
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


class TestAIProcessingIntegration:
    """Tests for AI processing integration (Gemini + TTS)."""

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
            gmail_history_id="12345",
        )

    @pytest.fixture
    def mock_contact(self, mock_user: User) -> Contact:
        """Create a mock registered contact."""
        return Contact(
            id=uuid7(),
            user_id=mock_user.id,
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
                },
            },
            "internalDate": "1704067200000",
        }

    @pytest.mark.asyncio
    async def test_process_message_calls_gemini_for_gyaru_conversion(
        self,
        mock_user: User,
        mock_contact: Contact,
        mock_gmail_message: dict,
    ):
        """Test that message processing calls Gemini for gyaru conversion."""
        from result import Ok

        from src.services.email_processor import EmailProcessorService

        mock_session = AsyncMock()

        # Setup mocks for DB queries
        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = mock_contact
        mock_email_exists_result = MagicMock()
        mock_email_exists_result.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [
            mock_contact_result,
            mock_email_exists_result,
        ]

        with (
            patch("src.services.email_processor.GeminiService") as mock_gemini_class,
            patch("src.services.email_processor.TTSService") as mock_tts_class,
        ):
            # Mock Gemini service
            mock_gemini = MagicMock()
            mock_gemini.convert_email = AsyncMock(
                return_value=Ok("やっほー先輩💖 報告書お願いだし！")
            )
            mock_gemini_class.return_value = mock_gemini

            # Mock TTS service
            mock_tts = MagicMock()
            mock_tts.synthesize_and_upload = AsyncMock(
                return_value=Ok("audio/test_20240115.wav")
            )
            mock_tts_class.return_value = mock_tts

            processor = EmailProcessorService(mock_session)
            result = await processor._process_single_message(
                mock_user.id, mock_gmail_message
            )

            assert result.processed is True
            mock_gemini.convert_email.assert_called_once()
            # Verify sender name is passed
            call_args = mock_gemini.convert_email.call_args
            assert "Boss" in str(call_args) or "boss" in str(call_args).lower()

    @pytest.mark.asyncio
    async def test_process_message_calls_tts_after_gyaru_conversion(
        self,
        mock_user: User,
        mock_contact: Contact,
        mock_gmail_message: dict,
    ):
        """Test that TTS is called after successful gyaru conversion."""
        from result import Ok

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

        converted_text = "やっほー先輩💖 報告書お願いだし！"

        with (
            patch("src.services.email_processor.GeminiService") as mock_gemini_class,
            patch("src.services.email_processor.TTSService") as mock_tts_class,
        ):
            mock_gemini = MagicMock()
            mock_gemini.convert_email = AsyncMock(return_value=Ok(converted_text))
            mock_gemini_class.return_value = mock_gemini

            mock_tts = MagicMock()
            mock_tts.synthesize_and_upload = AsyncMock(
                return_value=Ok("audio/test_20240115.wav")
            )
            mock_tts_class.return_value = mock_tts

            processor = EmailProcessorService(mock_session)
            await processor._process_single_message(mock_user.id, mock_gmail_message)

            # TTS should be called with converted text
            mock_tts.synthesize_and_upload.assert_called_once()
            call_args = mock_tts.synthesize_and_upload.call_args
            assert converted_text in str(call_args)

    @pytest.mark.asyncio
    async def test_process_message_saves_converted_body_and_audio_url(
        self,
        mock_user: User,
        mock_contact: Contact,
        mock_gmail_message: dict,
    ):
        """Test that converted_body and audio_url are saved to email."""
        from result import Ok

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

        converted_text = "やっほー先輩💖 報告書お願いだし！"
        audio_url = "audio/test_20240115.wav"

        with (
            patch("src.services.email_processor.GeminiService") as mock_gemini_class,
            patch("src.services.email_processor.TTSService") as mock_tts_class,
        ):
            mock_gemini = MagicMock()
            mock_gemini.convert_email = AsyncMock(return_value=Ok(converted_text))
            mock_gemini_class.return_value = mock_gemini

            mock_tts = MagicMock()
            mock_tts.synthesize_and_upload = AsyncMock(return_value=Ok(audio_url))
            mock_tts_class.return_value = mock_tts

            processor = EmailProcessorService(mock_session)
            await processor._process_single_message(mock_user.id, mock_gmail_message)

            # Check email was added with converted_body and audio_url
            added_email = mock_session.add.call_args[0][0]
            assert isinstance(added_email, Email)
            assert added_email.converted_body == converted_text
            assert added_email.audio_url == audio_url
            assert added_email.is_processed is True

    @pytest.mark.asyncio
    async def test_process_message_handles_gemini_error(
        self,
        mock_user: User,
        mock_contact: Contact,
        mock_gmail_message: dict,
    ):
        """Test that Gemini errors are handled gracefully."""
        from result import Err

        from src.services.email_processor import EmailProcessorService
        from src.services.gemini_service import GeminiError

        mock_session = AsyncMock()

        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = mock_contact
        mock_email_exists_result = MagicMock()
        mock_email_exists_result.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [
            mock_contact_result,
            mock_email_exists_result,
        ]

        with (
            patch("src.services.email_processor.GeminiService") as mock_gemini_class,
            patch("src.services.email_processor.TTSService") as mock_tts_class,
        ):
            mock_gemini = MagicMock()
            mock_gemini.convert_email = AsyncMock(
                return_value=Err(GeminiError.API_ERROR)
            )
            mock_gemini_class.return_value = mock_gemini

            mock_tts = MagicMock()
            mock_tts_class.return_value = mock_tts

            processor = EmailProcessorService(mock_session)
            await processor._process_single_message(mock_user.id, mock_gmail_message)

            # Email should still be created but without conversion
            mock_session.add.assert_called_once()
            added_email = mock_session.add.call_args[0][0]
            assert added_email.is_processed is False
            # TTS should not be called if Gemini fails
            mock_tts.synthesize_and_upload.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_message_handles_tts_error(
        self,
        mock_user: User,
        mock_contact: Contact,
        mock_gmail_message: dict,
    ):
        """Test that TTS errors are handled gracefully."""
        from result import Err, Ok

        from src.services.email_processor import EmailProcessorService
        from src.services.tts_service import TTSError

        mock_session = AsyncMock()

        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = mock_contact
        mock_email_exists_result = MagicMock()
        mock_email_exists_result.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [
            mock_contact_result,
            mock_email_exists_result,
        ]

        converted_text = "やっほー先輩💖 報告書お願いだし！"

        with (
            patch("src.services.email_processor.GeminiService") as mock_gemini_class,
            patch("src.services.email_processor.TTSService") as mock_tts_class,
        ):
            mock_gemini = MagicMock()
            mock_gemini.convert_email = AsyncMock(return_value=Ok(converted_text))
            mock_gemini_class.return_value = mock_gemini

            mock_tts = MagicMock()
            mock_tts.synthesize_and_upload = AsyncMock(
                return_value=Err(TTSError.API_ERROR)
            )
            mock_tts_class.return_value = mock_tts

            processor = EmailProcessorService(mock_session)
            await processor._process_single_message(mock_user.id, mock_gmail_message)

            # Email should be created with converted_body but without audio_url
            mock_session.add.assert_called_once()
            added_email = mock_session.add.call_args[0][0]
            assert added_email.converted_body == converted_text
            assert added_email.audio_url is None
            # is_processed is False because TTS failed
            assert added_email.is_processed is False


class TestCharacterIntegration:
    """Tests for character-based email processing pipeline (Task 6)."""

    @pytest.fixture
    def mock_contact(self) -> Contact:
        """Create a mock registered contact."""
        return Contact(
            id=uuid7(),
            user_id=uuid7(),
            contact_email="boss@company.com",
            contact_name="上司さん",
        )

    @pytest.fixture
    def mock_gmail_message(self) -> dict:
        """Create a mock Gmail API message."""
        return {
            "id": "msg-char-123",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Boss <boss@company.com>"},
                    {"name": "Subject", "value": "報告書の件"},
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(
                        "明日までに報告書を提出してください。".encode()
                    ).decode()
                },
            },
            "internalDate": "1704067200000",
        }

    @pytest.mark.asyncio
    async def test_process_message_uses_selected_character_for_gemini(
        self,
        mock_contact: Contact,
        mock_gmail_message: dict,
    ):
        """Test that Gemini receives the selected character's system prompt."""
        from result import Ok

        from src.services.character_service import BUTLER_CHARACTER
        from src.services.email_processor import EmailProcessorService

        user_id = uuid7()
        mock_session = AsyncMock()

        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = mock_contact
        mock_email_exists_result = MagicMock()
        mock_email_exists_result.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [
            mock_contact_result,
            mock_email_exists_result,
        ]

        with (
            patch("src.services.email_processor.GeminiService") as mock_gemini_class,
            patch("src.services.email_processor.TTSService") as mock_tts_class,
        ):
            mock_gemini = MagicMock()
            mock_gemini.convert_email = AsyncMock(
                return_value=Ok("ご主人様、報告書のご提出をお願いいたします。")
            )
            mock_gemini_class.return_value = mock_gemini

            mock_tts = MagicMock()
            mock_tts.synthesize_and_upload = AsyncMock(
                return_value=Ok("audio/test_20240115.wav")
            )
            mock_tts_class.return_value = mock_tts

            processor = EmailProcessorService(mock_session)
            result = await processor._process_single_message(
                user_id, mock_gmail_message, selected_character_id="butler"
            )

            assert result.processed is True
            # Verify Gemini was called with butler's system prompt
            call_kwargs = mock_gemini.convert_email.call_args.kwargs
            assert call_kwargs["system_prompt"] == BUTLER_CHARACTER.system_prompt

    @pytest.mark.asyncio
    async def test_process_message_uses_selected_character_voice_for_tts(
        self,
        mock_contact: Contact,
        mock_gmail_message: dict,
    ):
        """Test that TTS receives the selected character's voice name."""
        from result import Ok

        from src.services.character_service import BUTLER_CHARACTER
        from src.services.email_processor import EmailProcessorService

        user_id = uuid7()
        mock_session = AsyncMock()

        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = mock_contact
        mock_email_exists_result = MagicMock()
        mock_email_exists_result.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [
            mock_contact_result,
            mock_email_exists_result,
        ]

        converted_text = "ご主人様、報告書のご提出をお願いいたします。"

        with (
            patch("src.services.email_processor.GeminiService") as mock_gemini_class,
            patch("src.services.email_processor.TTSService") as mock_tts_class,
        ):
            mock_gemini = MagicMock()
            mock_gemini.convert_email = AsyncMock(return_value=Ok(converted_text))
            mock_gemini_class.return_value = mock_gemini

            mock_tts = MagicMock()
            mock_tts.synthesize_and_upload = AsyncMock(
                return_value=Ok("audio/test_20240115.wav")
            )
            mock_tts_class.return_value = mock_tts

            processor = EmailProcessorService(mock_session)
            await processor._process_single_message(
                user_id, mock_gmail_message, selected_character_id="butler"
            )

            # Verify TTS was called with butler's voice name
            call_kwargs = mock_tts.synthesize_and_upload.call_args.kwargs
            assert call_kwargs["voice_name"] == BUTLER_CHARACTER.tts_voice_name

    @pytest.mark.asyncio
    async def test_process_message_uses_default_character_when_none(
        self,
        mock_contact: Contact,
        mock_gmail_message: dict,
    ):
        """Test that default character (gyaru) is used when selected_character_id is None."""
        from result import Ok

        from src.services.character_service import GYARU_CHARACTER
        from src.services.email_processor import EmailProcessorService

        user_id = uuid7()
        mock_session = AsyncMock()

        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = mock_contact
        mock_email_exists_result = MagicMock()
        mock_email_exists_result.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [
            mock_contact_result,
            mock_email_exists_result,
        ]

        with (
            patch("src.services.email_processor.GeminiService") as mock_gemini_class,
            patch("src.services.email_processor.TTSService") as mock_tts_class,
        ):
            mock_gemini = MagicMock()
            mock_gemini.convert_email = AsyncMock(return_value=Ok("やっほー先輩！"))
            mock_gemini_class.return_value = mock_gemini

            mock_tts = MagicMock()
            mock_tts.synthesize_and_upload = AsyncMock(
                return_value=Ok("audio/test_20240115.wav")
            )
            mock_tts_class.return_value = mock_tts

            processor = EmailProcessorService(mock_session)
            await processor._process_single_message(
                user_id, mock_gmail_message, selected_character_id=None
            )

            # Verify Gemini was called with gyaru's system prompt (default)
            call_kwargs = mock_gemini.convert_email.call_args.kwargs
            assert call_kwargs["system_prompt"] == GYARU_CHARACTER.system_prompt

            # Verify TTS was called with gyaru's voice name (default)
            tts_kwargs = mock_tts.synthesize_and_upload.call_args.kwargs
            assert tts_kwargs["voice_name"] == GYARU_CHARACTER.tts_voice_name

    @pytest.mark.asyncio
    async def test_process_notification_passes_character_id_through_pipeline(
        self,
        mock_gmail_message: dict,
    ):
        """Test that process_notification passes user's selected_character_id through the pipeline."""
        from result import Ok

        from src.services.character_service import SENPAI_CHARACTER
        from src.services.email_processor import EmailProcessorService

        mock_user = User(
            id=uuid7(),
            firebase_uid="test-uid-senpai",
            email="user@example.com",
            gmail_refresh_token="refresh-token-xxx",
            gmail_access_token="access-token-xxx",
            gmail_token_expires_at=datetime.now(timezone.utc),
            gmail_history_id="12345",
            selected_character_id="senpai",
        )

        mock_contact = Contact(
            id=uuid7(),
            user_id=mock_user.id,
            contact_email="boss@company.com",
            contact_name="上司さん",
        )

        mock_history_response = {
            "history": [
                {
                    "id": "12346",
                    "messagesAdded": [
                        {"message": {"id": "msg-char-123", "threadId": "t-1"}}
                    ],
                }
            ],
            "historyId": "12347",
        }

        mock_session = AsyncMock()

        # Mock user lookup
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        # Mock contact lookup
        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = mock_contact

        # Mock email existence check
        mock_email_exists = MagicMock()
        mock_email_exists.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [
            mock_user_result,
            mock_contact_result,
            mock_email_exists,
        ]

        with (
            patch("src.services.email_processor.GmailApiClient") as mock_gmail_client,
            patch("src.services.email_processor.GeminiService") as mock_gemini_class,
            patch("src.services.email_processor.TTSService") as mock_tts_class,
            patch.object(
                EmailProcessorService,
                "_get_valid_access_token",
                return_value="valid-access-token",
            ),
        ):
            mock_gmail = MagicMock()
            mock_gmail.fetch_email_history = AsyncMock(
                return_value=mock_history_response
            )
            mock_gmail.fetch_message = AsyncMock(return_value=mock_gmail_message)
            mock_gmail_client.return_value = mock_gmail

            mock_gemini = MagicMock()
            mock_gemini.convert_email = AsyncMock(
                return_value=Ok("先輩からメールが来てるよ。")
            )
            mock_gemini_class.return_value = mock_gemini

            mock_tts = MagicMock()
            mock_tts.synthesize_and_upload = AsyncMock(
                return_value=Ok("audio/test_20240115.wav")
            )
            mock_tts_class.return_value = mock_tts

            processor = EmailProcessorService(mock_session)
            result = await processor.process_notification("user@example.com", "99999")

            assert result.skipped is False
            assert result.processed_count == 1

            # Verify Gemini was called with senpai's system prompt
            call_kwargs = mock_gemini.convert_email.call_args.kwargs
            assert call_kwargs["system_prompt"] == SENPAI_CHARACTER.system_prompt

            # Verify TTS was called with senpai's voice name
            tts_kwargs = mock_tts.synthesize_and_upload.call_args.kwargs
            assert tts_kwargs["voice_name"] == SENPAI_CHARACTER.tts_voice_name
