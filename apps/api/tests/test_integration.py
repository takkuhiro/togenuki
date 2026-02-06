"""End-to-End Integration Tests for Email Voice Playback.

Tests the complete flow from email reception to audio playback:
- Pub/Sub Webhook → メール取得 → ギャル語変換 → 音声生成 → DB保存
- ダッシュボード表示 → 音声再生

Requirements Coverage: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.6, 3.1, 3.3, 3.5, 4.1, 5.1, 6.1, 6.2, 6.3
"""

import base64
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from result import Ok
from uuid6 import uuid7

from src.auth.schemas import FirebaseUser
from src.database import get_db
from src.main import app
from src.models import Contact, Email, User


class TestEmailProcessingPipeline:
    """Integration tests for the complete email processing pipeline.

    Tests Requirements:
    - 1.1: Pub/Sub通知受信
    - 1.2: 即時200 OK返却 + BackgroundTask
    - 1.3: Gmail API本文取得
    - 1.4: 未登録連絡先スキップ
    - 1.5: emailsテーブル作成 (is_processed=false)
    - 2.1: Geminiギャル語変換リクエスト
    - 2.6: converted_body保存
    - 3.1: Cloud TTS音声合成リクエスト
    - 3.3: GCSアップロード
    - 3.5: is_processed=true更新
    """

    @pytest.fixture
    def mock_user(self) -> User:
        """Create a mock user with Gmail OAuth configured."""
        return User(
            id=uuid7(),
            firebase_uid="test-uid-integration",
            email="integration-test@example.com",
            gmail_refresh_token="refresh-token-xxx",
            gmail_access_token="access-token-xxx",
            gmail_token_expires_at=datetime.now(timezone.utc),
            gmail_history_id="10000",
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
    def pubsub_message(self) -> dict:
        """Create a valid Pub/Sub message for testing."""
        data = {
            "emailAddress": "integration-test@example.com",
            "historyId": "20000",
        }
        encoded_data = base64.b64encode(json.dumps(data).encode()).decode()
        return {
            "message": {
                "data": encoded_data,
                "messageId": "integration-msg-123",
                "publishTime": "2024-01-01T12:00:00Z",
            },
            "subscription": "projects/test/subscriptions/gmail-push",
        }

    @pytest.fixture
    def mock_gmail_message(self) -> dict:
        """Create a mock Gmail API message."""
        return {
            "id": "gmail-msg-integration-test",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Boss <boss@company.com>"},
                    {"name": "Subject", "value": "至急！報告書について"},
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(
                        "明日までに報告書を提出してください。遅れは認められません。".encode()
                    ).decode()
                },
            },
            "internalDate": "1704110400000",
        }

    @pytest.fixture
    def mock_history_response(self) -> dict:
        """Create a mock Gmail history response."""
        return {
            "history": [
                {
                    "id": "20001",
                    "messagesAdded": [
                        {
                            "message": {
                                "id": "gmail-msg-integration-test",
                                "threadId": "thread-integration",
                                "labelIds": ["INBOX", "UNREAD"],
                            }
                        }
                    ],
                }
            ],
            "historyId": "20002",
        }

    @pytest.mark.asyncio
    async def test_webhook_returns_200_immediately_req_1_2(
        self, pubsub_message: dict
    ) -> None:
        """Requirement 1.2: Webhook returns 200 OK immediately."""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with patch(
                "src.routers.webhook.process_gmail_notification",
                new_callable=AsyncMock,
            ):
                response = await client.post("/api/webhook/gmail", json=pubsub_message)

        assert response.status_code == 200
        assert response.json() == {"status": "accepted"}

    @pytest.mark.asyncio
    async def test_full_processing_pipeline(
        self,
        mock_user: User,
        mock_contact: Contact,
        mock_gmail_message: dict,
        mock_history_response: dict,
    ) -> None:
        """Test complete pipeline: Pub/Sub → Gmail → Gemini → TTS → DB."""
        from src.services.email_processor import EmailProcessorService

        # Setup database mocks
        mock_session = AsyncMock()

        # Mock user lookup
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = mock_user

        # Mock contact lookup
        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = mock_contact

        # Mock email existence check (not exists)
        mock_email_exists = MagicMock()
        mock_email_exists.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [
            mock_user_result,
            mock_contact_result,
            mock_email_exists,
        ]

        converted_text = "やっほー先輩💖 上司さんからメール来てるし！報告書、明日までにお願いだって✨ 先輩ならできるっしょ！🔥"
        audio_url = "https://storage.googleapis.com/togenuki-audio/test.mp3"

        with (
            patch("src.services.email_processor.GmailApiClient") as mock_gmail_client,
            patch("src.services.email_processor.GeminiService") as mock_gemini,
            patch("src.services.email_processor.TTSService") as mock_tts,
            patch.object(
                EmailProcessorService,
                "_get_valid_access_token",
                return_value="valid-access-token",
            ),
        ):
            # Mock Gmail API
            mock_gmail = MagicMock()
            mock_gmail.fetch_email_history = AsyncMock(
                return_value=mock_history_response
            )
            mock_gmail.fetch_message = AsyncMock(return_value=mock_gmail_message)
            mock_gmail_client.return_value = mock_gmail

            # Mock Gemini Service (Requirement 2.1)
            mock_gemini_instance = MagicMock()
            mock_gemini_instance.convert_to_gyaru = AsyncMock(
                return_value=Ok(converted_text)
            )
            mock_gemini.return_value = mock_gemini_instance

            # Mock TTS Service (Requirement 3.1, 3.3)
            mock_tts_instance = MagicMock()
            mock_tts_instance.synthesize_and_upload = AsyncMock(
                return_value=Ok(audio_url)
            )
            mock_tts.return_value = mock_tts_instance

            processor = EmailProcessorService(mock_session)
            result = await processor.process_notification(
                "integration-test@example.com", "20000"
            )

        # Assertions
        assert result.skipped is False
        assert result.processed_count == 1

        # Verify Gemini was called with sender name
        mock_gemini_instance.convert_to_gyaru.assert_called_once()
        call_args = mock_gemini_instance.convert_to_gyaru.call_args
        assert "Boss" in str(call_args) or "上司" in str(call_args)

        # Verify TTS was called with converted text
        mock_tts_instance.synthesize_and_upload.assert_called_once()
        tts_call_args = mock_tts_instance.synthesize_and_upload.call_args
        assert converted_text in str(tts_call_args)

        # Verify email was saved
        mock_session.add.assert_called_once()
        saved_email = mock_session.add.call_args[0][0]
        assert isinstance(saved_email, Email)
        assert saved_email.converted_body == converted_text
        assert saved_email.audio_url == audio_url
        assert saved_email.is_processed is True

    @pytest.mark.asyncio
    async def test_unregistered_contact_is_skipped_req_1_4(
        self,
        mock_user: User,
        mock_gmail_message: dict,
    ) -> None:
        """Requirement 1.4: Messages from unregistered contacts are skipped."""
        from src.services.email_processor import EmailProcessorService

        mock_session = AsyncMock()

        # Mock contact lookup - returns None (not registered)
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


class TestDashboardAndAudioPlayback:
    """Integration tests for dashboard display and audio playback.

    Tests Requirements:
    - 4.1: GET /api/emails でメール一覧取得
    - 6.1: Firebase ID Token検証
    - 6.2: ユーザーは自分のメールのみ取得可能
    - 6.3: Token検証
    """

    @pytest.fixture
    def mock_user(self) -> FirebaseUser:
        """Create an authenticated Firebase user."""
        return FirebaseUser(uid="dashboard-test-uid", email="dashboard@example.com")

    @pytest.fixture
    def mock_emails(self) -> list[dict]:
        """Create mock email data for dashboard display."""
        return [
            {
                "id": str(uuid7()),
                "sender_name": "上司さん",
                "sender_email": "boss@company.com",
                "subject": "至急！報告書について",
                "converted_body": "やっほー先輩💖 報告書お願いだし！✨",
                "audio_url": "https://storage.googleapis.com/togenuki-audio/audio1.mp3",
                "is_processed": True,
                "received_at": "2024-01-15T10:30:00+00:00",
            },
            {
                "id": str(uuid7()),
                "sender_name": "クライアントさん",
                "sender_email": "client@example.com",
                "subject": "ミーティングの件",
                "converted_body": None,
                "audio_url": None,
                "is_processed": False,
                "received_at": "2024-01-14T09:00:00+00:00",
            },
        ]

    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401_req_6_1(self) -> None:
        """Requirement 6.1/6.3: Unauthenticated requests should return 401."""
        from src.routers.emails import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/emails")

        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "missing_token"

    @pytest.mark.asyncio
    async def test_authenticated_user_gets_own_emails_req_4_1_6_2(
        self, mock_user: FirebaseUser, mock_emails: list[dict]
    ) -> None:
        """Requirements 4.1, 6.2: Authenticated user retrieves only their emails."""
        from src.routers.emails import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        mock_session = MagicMock()
        test_app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.emails.get_user_emails",
                new=AsyncMock(return_value=mock_emails),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/emails",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert "emails" in data
        assert data["total"] == 2

        # Check processed email has all required fields
        processed_email = data["emails"][0]
        assert processed_email["isProcessed"] is True
        assert processed_email["audioUrl"] is not None
        assert processed_email["convertedBody"] is not None

        # Check unprocessed email
        unprocessed_email = data["emails"][1]
        assert unprocessed_email["isProcessed"] is False
        assert unprocessed_email["audioUrl"] is None

    @pytest.mark.asyncio
    async def test_email_list_sorted_by_received_at_desc(
        self, mock_user: FirebaseUser
    ) -> None:
        """Emails should be sorted by received_at in descending order."""
        from src.routers.emails import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        mock_session = MagicMock()
        test_app.dependency_overrides[get_db] = lambda: mock_session

        # Create emails with different timestamps
        mock_emails = [
            {
                "id": str(uuid7()),
                "sender_name": "New",
                "sender_email": "new@example.com",
                "subject": "Newer email",
                "converted_body": "新しいメール",
                "audio_url": "https://example.com/new.mp3",
                "is_processed": True,
                "received_at": "2024-01-15T12:00:00+00:00",
            },
            {
                "id": str(uuid7()),
                "sender_name": "Old",
                "sender_email": "old@example.com",
                "subject": "Older email",
                "converted_body": "古いメール",
                "audio_url": "https://example.com/old.mp3",
                "is_processed": True,
                "received_at": "2024-01-10T12:00:00+00:00",
            },
        ]

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.emails.get_user_emails",
                new=AsyncMock(return_value=mock_emails),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/emails",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        emails = response.json()["emails"]

        # First email should be newer
        assert emails[0]["senderName"] == "New"
        assert emails[1]["senderName"] == "Old"


class TestAuthenticationFlow:
    """Integration tests for authentication flow (Firebase → Backend).

    Tests Requirements:
    - 6.1: Firebase Authentication
    - 6.2: ID Token取得・保持
    - 6.3: Firebase ID Token検証
    """

    @pytest.mark.asyncio
    async def test_valid_firebase_token_authenticates_user(self) -> None:
        """Requirement 6.3: Valid Firebase token should authenticate user."""
        from src.routers.emails import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        mock_session = MagicMock()
        test_app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch("src.routers.emails.get_user_emails", new=AsyncMock(return_value=[])),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": "valid-uid-123",
                "email": "valid@example.com",
            }

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/emails",
                    headers={"Authorization": "Bearer valid_firebase_token"},
                )

        assert response.status_code == 200
        mock_auth.verify_id_token.assert_called_once_with("valid_firebase_token")

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self) -> None:
        """Requirement 6.3: Expired token should return 401."""
        from src.routers.emails import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        with patch("src.auth.middleware.auth") as mock_auth:
            mock_auth.verify_id_token.side_effect = Exception("Token expired")

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/emails",
                    headers={"Authorization": "Bearer expired_token"},
                )

        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "expired_token"

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self) -> None:
        """Requirement 6.3: Invalid token should return 401."""
        from src.routers.emails import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        with patch("src.auth.middleware.auth") as mock_auth:
            mock_auth.verify_id_token.side_effect = Exception("Invalid token")

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/emails",
                    headers={"Authorization": "Bearer invalid_token"},
                )

        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "invalid_token"


class TestGyaruConversionIntegration:
    """Integration tests for gyaru conversion flow.

    Tests Requirements:
    - 2.1: Geminiギャル語変換リクエスト
    - 2.6: converted_body保存
    """

    @pytest.mark.asyncio
    async def test_gemini_conversion_saves_to_email(self) -> None:
        """Requirement 2.1, 2.6: Gyaru conversion result is saved to email."""
        from src.services.email_processor import EmailProcessorService

        mock_session = AsyncMock()

        mock_user = User(
            id=uuid7(),
            firebase_uid="gyaru-test-uid",
            email="gyaru@example.com",
            gmail_refresh_token="refresh-token",
            gmail_access_token="access-token",
            gmail_history_id="10000",
        )

        mock_contact = Contact(
            id=uuid7(),
            user_id=mock_user.id,
            contact_email="sender@company.com",
            contact_name="送信者さん",
        )

        mock_gmail_message = {
            "id": "gyaru-test-msg",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Sender <sender@company.com>"},
                    {"name": "Subject", "value": "テスト"},
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(
                        "明日の会議に出席してください。".encode()
                    ).decode()
                },
            },
            "internalDate": "1704110400000",
        }

        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = mock_contact
        mock_email_exists = MagicMock()
        mock_email_exists.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [mock_contact_result, mock_email_exists]

        converted = (
            "やっほー先輩💖 送信者さんからメール来てるし！明日の会議よろしくね〜✨"
        )
        audio_url = "https://storage.example.com/audio.mp3"

        with (
            patch("src.services.email_processor.GeminiService") as mock_gemini,
            patch("src.services.email_processor.TTSService") as mock_tts,
        ):
            mock_gemini_instance = MagicMock()
            mock_gemini_instance.convert_to_gyaru = AsyncMock(
                return_value=Ok(converted)
            )
            mock_gemini.return_value = mock_gemini_instance

            mock_tts_instance = MagicMock()
            mock_tts_instance.synthesize_and_upload = AsyncMock(
                return_value=Ok(audio_url)
            )
            mock_tts.return_value = mock_tts_instance

            processor = EmailProcessorService(mock_session)
            result = await processor._process_single_message(
                mock_user.id, mock_gmail_message
            )

        assert result.processed is True

        # Verify email was saved with converted body
        saved_email = mock_session.add.call_args[0][0]
        assert saved_email.converted_body == converted
        assert saved_email.is_processed is True


class TestTTSIntegration:
    """Integration tests for TTS and GCS upload flow.

    Tests Requirements:
    - 3.1: Cloud TTS音声合成リクエスト
    - 3.3: GCSアップロード
    - 3.5: is_processed=true更新
    """

    @pytest.mark.asyncio
    async def test_tts_result_saves_audio_url(self) -> None:
        """Requirements 3.1, 3.3, 3.5: TTS result saves audio_url and sets is_processed."""
        from src.services.email_processor import EmailProcessorService

        mock_session = AsyncMock()

        mock_user = User(
            id=uuid7(),
            firebase_uid="tts-test-uid",
            email="tts@example.com",
            gmail_refresh_token="refresh-token",
            gmail_access_token="access-token",
            gmail_history_id="10000",
        )

        mock_contact = Contact(
            id=uuid7(),
            user_id=mock_user.id,
            contact_email="sender@company.com",
            contact_name="送信者さん",
        )

        mock_gmail_message = {
            "id": "tts-test-msg",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Sender <sender@company.com>"},
                    {"name": "Subject", "value": "テスト"},
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(
                        "テスト本文です。".encode()
                    ).decode()
                },
            },
            "internalDate": "1704110400000",
        }

        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = mock_contact
        mock_email_exists = MagicMock()
        mock_email_exists.scalar_one_or_none.return_value = None
        mock_session.execute.side_effect = [mock_contact_result, mock_email_exists]

        converted = "変換後テキスト"
        audio_url = "https://storage.googleapis.com/bucket/audio/test.mp3"

        with (
            patch("src.services.email_processor.GeminiService") as mock_gemini,
            patch("src.services.email_processor.TTSService") as mock_tts,
        ):
            mock_gemini_instance = MagicMock()
            mock_gemini_instance.convert_to_gyaru = AsyncMock(
                return_value=Ok(converted)
            )
            mock_gemini.return_value = mock_gemini_instance

            mock_tts_instance = MagicMock()
            mock_tts_instance.synthesize_and_upload = AsyncMock(
                return_value=Ok(audio_url)
            )
            mock_tts.return_value = mock_tts_instance

            processor = EmailProcessorService(mock_session)
            await processor._process_single_message(mock_user.id, mock_gmail_message)

        # Verify email was saved with audio_url and is_processed=True
        saved_email = mock_session.add.call_args[0][0]
        assert saved_email.audio_url == audio_url
        assert saved_email.is_processed is True
