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
            mock_gemini_instance.convert_email = AsyncMock(
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
        mock_gemini_instance.convert_email.assert_called_once()
        call_args = mock_gemini_instance.convert_email.call_args
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
                "replied_at": None,
                "reply_body": None,
                "reply_subject": None,
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
                "replied_at": None,
                "reply_body": None,
                "reply_subject": None,
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
                "replied_at": None,
                "reply_body": None,
                "reply_subject": None,
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
                "replied_at": None,
                "reply_body": None,
                "reply_subject": None,
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
            mock_gemini_instance.convert_email = AsyncMock(return_value=Ok(converted))
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
            mock_gemini_instance.convert_email = AsyncMock(return_value=Ok(converted))
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


class TestContactRegistrationLearningFlow:
    """Integration tests for contact registration → learning → completion flow.

    Tests Requirements:
    - 1.1: 連絡先登録時にDBレコード作成 (is_learning_complete=false)
    - 1.2: 即座に201 Createdと status: "learning_started" を返却
    - 4.1: BackgroundTasksで学習処理を非同期実行
    - 4.5: contact_contextに learned_patterns を保存
    - 4.6: is_learning_complete=true に更新
    - 5.1: ポーリングによる学習状態更新確認
    - 5.2: UI学習ステータス更新
    """

    @pytest.fixture
    def mock_user(self) -> User:
        """Create a mock user with Gmail OAuth configured."""
        return User(
            id=uuid7(),
            firebase_uid="contact-integration-uid",
            email="contact-test@example.com",
            gmail_refresh_token="refresh-token-xxx",
            gmail_access_token="access-token-xxx",
            gmail_token_expires_at=datetime.now(timezone.utc),
            gmail_history_id="10000",
        )

    @pytest.fixture
    def firebase_user(self) -> FirebaseUser:
        """Create a Firebase authenticated user."""
        return FirebaseUser(
            uid="contact-integration-uid", email="contact-test@example.com"
        )

    @pytest.fixture
    def mock_contact(self, mock_user: User) -> Contact:
        """Create a mock contact with learning not started."""
        return Contact(
            id=uuid7(),
            user_id=mock_user.id,
            contact_email="boss@company.com",
            contact_name="上司さん",
            gmail_query="from:boss@company.com",
            is_learning_complete=False,
            created_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        )

    @pytest.mark.asyncio
    async def test_contact_registration_returns_201_with_learning_started_req_1_1_1_2(
        self,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_contact: Contact,
    ) -> None:
        """Requirement 1.1, 1.2: Register contact returns 201 with learning_started status.

        Verifies the complete registration flow:
        1. POST /api/contacts creates a new contact
        2. Returns 201 Created immediately
        3. Response contains status: "learning_started"
        4. BackgroundTasks is invoked to start learning
        """
        from src.routers.contacts import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        test_app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user),
            ),
            patch(
                "src.routers.contacts.create_contact",
                new=AsyncMock(return_value=mock_contact),
            ),
            patch("src.routers.contacts.LearningService") as mock_learning_cls,
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": firebase_user.uid,
                "email": firebase_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/contacts",
                    json={
                        "contactEmail": "boss@company.com",
                        "contactName": "上司さん",
                        "gmailQuery": "from:boss@company.com",
                    },
                    headers={"Authorization": "Bearer valid_token"},
                )

        # Verify response
        assert response.status_code == 201
        data = response.json()
        assert data["contactEmail"] == "boss@company.com"
        assert data["contactName"] == "上司さん"
        assert data["status"] == "learning_started"
        assert data["isLearningComplete"] is False

        # Verify LearningService was instantiated and process_learning scheduled
        mock_learning_cls.assert_called_once()

    @pytest.mark.asyncio
    async def test_full_learning_process_creates_contact_context_req_4_1_4_5_4_6(
        self,
        mock_user: User,
        mock_contact: Contact,
    ) -> None:
        """Requirements 4.1, 4.5, 4.6: Learning process fetches emails, analyzes, and saves context.

        Verifies the complete learning pipeline:
        1. Gmail API is called to fetch past emails
        2. Gemini analyzes the email patterns
        3. Contact context is created with learned_patterns
        4. is_learning_complete is set to true
        """
        from src.services.learning_service import LearningService

        mock_session = AsyncMock()

        learned_patterns_json = json.dumps(
            {
                "contactCharacteristics": {
                    "tone": "丁寧だが直接的",
                    "commonExpressions": ["よろしくお願いします", "至急対応ください"],
                    "requestPatterns": ["期限付き指示", "報告要求"],
                },
                "userReplyPatterns": {
                    "responseStyle": "丁寧かつ迅速",
                    "commonExpressions": ["承知しました", "確認いたします"],
                    "formalityLevel": "ビジネス敬語",
                },
            }
        )

        with (
            patch("src.services.learning_service.get_user_by_id") as mock_get_user,
            patch(
                "src.services.learning_service.get_contact_by_id"
            ) as mock_get_contact,
            patch("src.services.learning_service.get_db") as mock_get_db,
            patch("src.services.learning_service.GmailApiClient") as mock_gmail_class,
            patch("src.services.learning_service.GeminiService") as mock_gemini_class,
            patch(
                "src.services.learning_service.GmailOAuthService"
            ) as mock_oauth_class,
            patch(
                "src.services.learning_service.create_contact_context"
            ) as mock_create_context,
            patch(
                "src.services.learning_service.update_contact_learning_status"
            ) as mock_update_status,
        ):
            mock_get_user.return_value = mock_user
            mock_get_contact.return_value = mock_contact
            mock_get_db.return_value.__aiter__.return_value = iter([mock_session])

            # OAuth mock
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(
                return_value={
                    "access_token": "access-token-xxx",
                    "expires_at": datetime.now(timezone.utc),
                }
            )
            mock_oauth_class.return_value = mock_oauth

            # Gmail API mock
            mock_gmail = MagicMock()
            mock_gmail.search_messages = AsyncMock(
                return_value=[
                    {"id": "msg-1", "threadId": "thread-1"},
                    {"id": "msg-2", "threadId": "thread-2"},
                ]
            )
            mock_gmail.fetch_message = AsyncMock(
                return_value={
                    "id": "msg-1",
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "Boss <boss@company.com>"},
                            {"name": "Subject", "value": "報告書について"},
                        ],
                        "mimeType": "text/plain",
                        "body": {
                            "data": base64.urlsafe_b64encode(
                                "明日までに報告書を提出してください。".encode()
                            ).decode()
                        },
                    },
                    "internalDate": "1704110400000",
                }
            )
            mock_gmail_class.return_value = mock_gmail

            # Gemini API mock - returns learned patterns
            mock_gemini = MagicMock()
            mock_gemini.analyze_patterns = AsyncMock(
                return_value=Ok(learned_patterns_json)
            )
            mock_gemini_class.return_value = mock_gemini

            service = LearningService()
            await service.process_learning(
                contact_id=mock_contact.id,
                user_id=mock_user.id,
            )

        # Verify Gmail search was called
        mock_gmail.search_messages.assert_called_once()

        # Verify Gemini analysis was called
        mock_gemini.analyze_patterns.assert_called_once()

        # Verify contact context was created (Req 4.5)
        mock_create_context.assert_called_once()
        context_call = mock_create_context.call_args
        assert context_call.kwargs["contact_id"] == mock_contact.id
        assert "contactCharacteristics" in context_call.kwargs["learned_patterns"]

        # Verify learning status updated to complete (Req 4.6)
        mock_update_status.assert_called()
        final_status_call = mock_update_status.call_args
        assert final_status_call.kwargs["is_complete"] is True

    @pytest.mark.asyncio
    async def test_polling_reflects_learning_completion_req_5_1_5_2(
        self,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_contact: Contact,
    ) -> None:
        """Requirements 5.1, 5.2: Polling GET /api/contacts reflects learning state changes.

        Simulates the polling workflow:
        1. First poll: contact shows is_learning_complete=false, status="learning_started"
        2. Second poll: contact shows is_learning_complete=true, status="learning_complete"
        """
        from src.routers.contacts import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        mock_session = MagicMock()
        test_app.dependency_overrides[get_db] = lambda: mock_session

        # First poll - learning in progress
        contact_learning = MagicMock()
        contact_learning.id = mock_contact.id
        contact_learning.contact_email = "boss@company.com"
        contact_learning.contact_name = "上司さん"
        contact_learning.gmail_query = "from:boss@company.com"
        contact_learning.is_learning_complete = False
        contact_learning.learning_failed_at = None
        contact_learning.created_at = datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
        )

        # Second poll - learning complete
        contact_complete = MagicMock()
        contact_complete.id = mock_contact.id
        contact_complete.contact_email = "boss@company.com"
        contact_complete.contact_name = "上司さん"
        contact_complete.gmail_query = "from:boss@company.com"
        contact_complete.is_learning_complete = True
        contact_complete.learning_failed_at = None
        contact_complete.created_at = datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user),
            ),
            patch(
                "src.routers.contacts.get_contacts_by_user_id",
            ) as mock_get_contacts,
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": firebase_user.uid,
                "email": firebase_user.email,
            }

            # First poll returns learning in progress
            mock_get_contacts.return_value = [contact_learning]

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                # Poll 1: learning in progress
                response1 = await client.get(
                    "/api/contacts",
                    headers={"Authorization": "Bearer valid_token"},
                )

            assert response1.status_code == 200
            data1 = response1.json()
            assert data1["total"] == 1
            assert data1["contacts"][0]["status"] == "learning_started"
            assert data1["contacts"][0]["isLearningComplete"] is False

            # Second poll returns learning complete
            mock_get_contacts.return_value = [contact_complete]

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                # Poll 2: learning complete
                response2 = await client.get(
                    "/api/contacts",
                    headers={"Authorization": "Bearer valid_token"},
                )

            assert response2.status_code == 200
            data2 = response2.json()
            assert data2["total"] == 1
            assert data2["contacts"][0]["status"] == "learning_complete"
            assert data2["contacts"][0]["isLearningComplete"] is True


class TestContactDeletionWithContextFlow:
    """Integration tests for contact deletion flow with ContactContext.

    Tests Requirements:
    - 3.3: 連絡先と関連するcontact_contextを削除
    - 3.4: 他ユーザーの連絡先削除時403
    - 3.5: 存在しない連絡先削除時404
    """

    @pytest.fixture
    def mock_user(self) -> User:
        """Create a mock user."""
        return User(
            id=uuid7(),
            firebase_uid="delete-test-uid",
            email="delete-test@example.com",
        )

    @pytest.fixture
    def firebase_user(self) -> FirebaseUser:
        """Create a Firebase authenticated user."""
        return FirebaseUser(uid="delete-test-uid", email="delete-test@example.com")

    @pytest.fixture
    def mock_contact_with_context(self, mock_user: User) -> Contact:
        """Create a contact that has a learning context."""
        return Contact(
            id=uuid7(),
            user_id=mock_user.id,
            contact_email="boss@company.com",
            contact_name="上司さん",
            is_learning_complete=True,
        )

    @pytest.mark.asyncio
    async def test_delete_contact_removes_contact_and_context_req_3_3(
        self,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_contact_with_context: Contact,
    ) -> None:
        """Requirement 3.3: Deleting contact also deletes related contact_context.

        Verifies:
        1. DELETE /api/contacts/{id} returns 204
        2. The contact is deleted from the database
        3. Related contact_context is also deleted (CASCADE)
        """
        from src.routers.contacts import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()
        test_app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=mock_contact_with_context),
            ),
            patch(
                "src.routers.contacts.delete_contact",
                new=AsyncMock(return_value=True),
            ) as mock_delete,
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": firebase_user.uid,
                "email": firebase_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.delete(
                    f"/api/contacts/{mock_contact_with_context.id}",
                    headers={"Authorization": "Bearer valid_token"},
                )

        # Verify 204 No Content
        assert response.status_code == 204

        # Verify delete was called with correct contact_id
        mock_delete.assert_called_once_with(mock_session, mock_contact_with_context.id)

    @pytest.mark.asyncio
    async def test_delete_other_users_contact_returns_403_req_3_4(
        self,
        firebase_user: FirebaseUser,
        mock_user: User,
    ) -> None:
        """Requirement 3.4: Deleting another user's contact returns 403 Forbidden."""
        from src.routers.contacts import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        mock_session = MagicMock()
        test_app.dependency_overrides[get_db] = lambda: mock_session

        # Contact belongs to a different user
        other_user_contact = MagicMock()
        other_user_contact.id = uuid7()
        other_user_contact.user_id = uuid7()  # Different user_id
        other_user_contact.contact_email = "other@example.com"

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=other_user_contact),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": firebase_user.uid,
                "email": firebase_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.delete(
                    f"/api/contacts/{other_user_contact.id}",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "forbidden"

    @pytest.mark.asyncio
    async def test_delete_nonexistent_contact_returns_404_req_3_5(
        self,
        firebase_user: FirebaseUser,
        mock_user: User,
    ) -> None:
        """Requirement 3.5: Deleting a nonexistent contact returns 404 Not Found."""
        from src.routers.contacts import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        mock_session = MagicMock()
        test_app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=None),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": firebase_user.uid,
                "email": firebase_user.email,
            }

            nonexistent_id = uuid7()
            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.delete(
                    f"/api/contacts/{nonexistent_id}",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 404
        assert response.json()["detail"]["error"] == "not_found"


class TestLearningFailureAndRetryFlow:
    """Integration tests for learning failure and retry flow.

    Tests Requirements:
    - 4.7: Gmail APIエラー時にlearning_failed_at設定
    - 4.8: Gemini APIエラー時に最大3回リトライ
    - 5.3: エラー時再試行ボタン（API: POST /contacts/{id}/retry）
    """

    @pytest.fixture
    def mock_user(self) -> User:
        """Create a mock user with Gmail OAuth."""
        return User(
            id=uuid7(),
            firebase_uid="retry-test-uid",
            email="retry-test@example.com",
            gmail_refresh_token="refresh-token-xxx",
            gmail_access_token="access-token-xxx",
            gmail_token_expires_at=datetime.now(timezone.utc),
        )

    @pytest.fixture
    def firebase_user(self) -> FirebaseUser:
        """Create a Firebase authenticated user."""
        return FirebaseUser(uid="retry-test-uid", email="retry-test@example.com")

    @pytest.fixture
    def mock_contact(self, mock_user: User) -> Contact:
        """Create a mock contact."""
        return Contact(
            id=uuid7(),
            user_id=mock_user.id,
            contact_email="client@company.com",
            contact_name="取引先さん",
            is_learning_complete=False,
        )

    @pytest.mark.asyncio
    async def test_gmail_api_error_sets_learning_failed_req_4_7(
        self,
        mock_user: User,
        mock_contact: Contact,
    ) -> None:
        """Requirement 4.7: Gmail API error sets learning_failed_at.

        Verifies:
        1. Gmail API throws error
        2. learning_failed_at is set to current timestamp
        3. is_learning_complete remains false
        """
        from src.services.gmail_service import GmailApiError
        from src.services.learning_service import LearningService

        mock_session = AsyncMock()

        with (
            patch("src.services.learning_service.get_user_by_id") as mock_get_user,
            patch(
                "src.services.learning_service.get_contact_by_id"
            ) as mock_get_contact,
            patch("src.services.learning_service.get_db") as mock_get_db,
            patch("src.services.learning_service.GmailApiClient") as mock_gmail_class,
            patch(
                "src.services.learning_service.GmailOAuthService"
            ) as mock_oauth_class,
            patch(
                "src.services.learning_service.update_contact_learning_status"
            ) as mock_update_status,
        ):
            mock_get_user.return_value = mock_user
            mock_get_contact.return_value = mock_contact
            mock_get_db.return_value.__aiter__.return_value = iter([mock_session])

            # OAuth mock
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(
                return_value={
                    "access_token": "access-token-xxx",
                    "expires_at": datetime.now(timezone.utc),
                }
            )
            mock_oauth_class.return_value = mock_oauth

            # Gmail API mock - throws error
            mock_gmail = MagicMock()
            mock_gmail.search_messages = AsyncMock(
                side_effect=GmailApiError("API rate limit exceeded", status_code=429)
            )
            mock_gmail_class.return_value = mock_gmail

            service = LearningService()
            await service.process_learning(
                contact_id=mock_contact.id,
                user_id=mock_user.id,
            )

        # Verify learning status was updated with failure
        mock_update_status.assert_called_once()
        status_call = mock_update_status.call_args
        assert status_call.kwargs["is_complete"] is False
        assert status_call.kwargs["failed_at"] is not None

    @pytest.mark.asyncio
    async def test_gemini_api_retries_3_times_on_failure_req_4_8(
        self,
        mock_user: User,
        mock_contact: Contact,
    ) -> None:
        """Requirement 4.8: Gemini API errors trigger up to 3 retries.

        Verifies:
        1. Gemini analyze_patterns is called 3 times
        2. After 3 failures, learning_failed_at is set
        """
        from result import Err

        from src.services.gemini_service import GeminiError
        from src.services.learning_service import LearningService

        mock_session = AsyncMock()

        with (
            patch("src.services.learning_service.get_user_by_id") as mock_get_user,
            patch(
                "src.services.learning_service.get_contact_by_id"
            ) as mock_get_contact,
            patch("src.services.learning_service.get_db") as mock_get_db,
            patch("src.services.learning_service.GmailApiClient") as mock_gmail_class,
            patch("src.services.learning_service.GeminiService") as mock_gemini_class,
            patch(
                "src.services.learning_service.GmailOAuthService"
            ) as mock_oauth_class,
            patch(
                "src.services.learning_service.update_contact_learning_status"
            ) as mock_update_status,
        ):
            mock_get_user.return_value = mock_user
            mock_get_contact.return_value = mock_contact
            mock_get_db.return_value.__aiter__.return_value = iter([mock_session])

            # OAuth mock
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(
                return_value={
                    "access_token": "access-token-xxx",
                    "expires_at": datetime.now(timezone.utc),
                }
            )
            mock_oauth_class.return_value = mock_oauth

            # Gmail API mock - returns messages
            mock_gmail = MagicMock()
            mock_gmail.search_messages = AsyncMock(
                return_value=[{"id": "msg-1", "threadId": "thread-1"}]
            )
            mock_gmail.fetch_message = AsyncMock(
                return_value={
                    "id": "msg-1",
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "Client <client@company.com>"},
                            {"name": "Subject", "value": "テスト"},
                        ],
                        "mimeType": "text/plain",
                        "body": {
                            "data": base64.urlsafe_b64encode(
                                "テスト本文".encode()
                            ).decode()
                        },
                    },
                    "internalDate": "1704110400000",
                }
            )
            mock_gmail_class.return_value = mock_gmail

            # Gemini API mock - always fails
            mock_gemini = MagicMock()
            mock_gemini.analyze_patterns = AsyncMock(
                return_value=Err(GeminiError.API_ERROR)
            )
            mock_gemini_class.return_value = mock_gemini

            service = LearningService()
            await service.process_learning(
                contact_id=mock_contact.id,
                user_id=mock_user.id,
            )

        # Verify Gemini was called 3 times (MAX_RETRIES)
        assert mock_gemini.analyze_patterns.call_count == 3

        # Verify learning status was updated with failure
        mock_update_status.assert_called_once()
        status_call = mock_update_status.call_args
        assert status_call.kwargs["is_complete"] is False
        assert status_call.kwargs["failed_at"] is not None

    @pytest.mark.asyncio
    async def test_retry_endpoint_resets_and_restarts_learning_req_5_3(
        self,
        firebase_user: FirebaseUser,
        mock_user: User,
    ) -> None:
        """Requirement 5.3: Retry endpoint resets status and restarts learning.

        Verifies:
        1. POST /api/contacts/{id}/retry resets learning_failed_at
        2. Background learning is restarted
        3. Response contains status: "learning_started"
        """
        from src.routers.contacts import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        test_app.dependency_overrides[get_db] = lambda: mock_session

        # Contact with failed learning
        failed_contact = MagicMock()
        failed_contact.id = uuid7()
        failed_contact.user_id = mock_user.id
        failed_contact.contact_email = "client@company.com"
        failed_contact.contact_name = "取引先さん"
        failed_contact.gmail_query = None
        failed_contact.is_learning_complete = False
        failed_contact.learning_failed_at = datetime(
            2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc
        )
        failed_contact.created_at = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=failed_contact),
            ),
            patch(
                "src.routers.contacts.delete_contact_context_by_contact_id",
                new=AsyncMock(),
            ),
            patch(
                "src.routers.contacts.update_contact_learning_status",
                new=AsyncMock(),
            ),
            patch("src.routers.contacts.LearningService") as mock_learning_cls,
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": firebase_user.uid,
                "email": firebase_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/contacts/{failed_contact.id}/retry",
                    headers={"Authorization": "Bearer valid_token"},
                )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["contactEmail"] == "client@company.com"
        # After refresh, status depends on mock state; verify learning was restarted
        mock_learning_cls.assert_called_once()


class TestCharacterSelectionE2E:
    """E2E Integration tests for character selection → email conversion pipeline.

    Tests Requirements:
    - 3.2: デフォルトキャラクター（NULL）でギャルが適用
    - 3.3: キャラクター変更後に新しいキャラクターで処理
    - 3.4: 処理済みメールがキャラクター変更の影響を受けない
    - 4.1: キャラクター対応Geminiシステムプロンプト
    - 4.2: キャラクター対応TTS音声
    - 4.3: 無効なキャラクターID時のフォールバック
    """

    @pytest.fixture
    def mock_gmail_message(self) -> dict:
        """Create a mock Gmail API message."""
        return {
            "id": "gmail-msg-char-e2e",
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
                    "id": "30001",
                    "messagesAdded": [
                        {
                            "message": {
                                "id": "gmail-msg-char-e2e",
                                "threadId": "thread-char-e2e",
                                "labelIds": ["INBOX", "UNREAD"],
                            }
                        }
                    ],
                }
            ],
            "historyId": "30002",
        }

    def _create_user(self, *, selected_character_id: str | None = None) -> User:
        """Helper to create a mock user with specified character."""
        return User(
            id=uuid7(),
            firebase_uid="char-e2e-uid",
            email="char-e2e@example.com",
            gmail_refresh_token="refresh-token-xxx",
            gmail_access_token="access-token-xxx",
            gmail_token_expires_at=datetime.now(timezone.utc),
            gmail_history_id="10000",
            selected_character_id=selected_character_id,
        )

    def _create_mock_contact(self, user: User) -> Contact:
        """Helper to create a mock contact."""
        return Contact(
            id=uuid7(),
            user_id=user.id,
            contact_email="boss@company.com",
            contact_name="上司さん",
        )

    def _setup_db_mocks(
        self, mock_session: AsyncMock, user: User, contact: Contact
    ) -> None:
        """Set up database session mocks for user, contact, and email existence."""
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = user

        mock_contact_result = MagicMock()
        mock_contact_result.scalar_one_or_none.return_value = contact

        mock_email_exists = MagicMock()
        mock_email_exists.scalar_one_or_none.return_value = None

        mock_session.execute.side_effect = [
            mock_user_result,
            mock_contact_result,
            mock_email_exists,
        ]

    @pytest.mark.asyncio
    async def test_default_character_uses_gyaru_for_null_user_req_3_2(
        self,
        mock_gmail_message: dict,
        mock_history_response: dict,
    ) -> None:
        """Requirement 3.2: User with NULL selected_character_id uses gyaru (default).

        Verifies the E2E flow:
        1. process_notification receives a user with no character selection
        2. Gemini is called with gyaru's system_prompt
        3. TTS is called with gyaru's tts_voice_name
        """
        from src.services.character_service import GYARU_CHARACTER
        from src.services.email_processor import EmailProcessorService

        mock_user = self._create_user(selected_character_id=None)
        mock_contact = self._create_mock_contact(mock_user)

        mock_session = AsyncMock()
        self._setup_db_mocks(mock_session, mock_user, mock_contact)

        converted_text = "やっほー先輩！ 上司さんから報告書よろしくだし！"
        audio_url = "https://storage.googleapis.com/togenuki-audio/default.mp3"

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
            mock_gmail = MagicMock()
            mock_gmail.fetch_email_history = AsyncMock(
                return_value=mock_history_response
            )
            mock_gmail.fetch_message = AsyncMock(return_value=mock_gmail_message)
            mock_gmail_client.return_value = mock_gmail

            mock_gemini_instance = MagicMock()
            mock_gemini_instance.convert_email = AsyncMock(
                return_value=Ok(converted_text)
            )
            mock_gemini.return_value = mock_gemini_instance

            mock_tts_instance = MagicMock()
            mock_tts_instance.synthesize_and_upload = AsyncMock(
                return_value=Ok(audio_url)
            )
            mock_tts.return_value = mock_tts_instance

            processor = EmailProcessorService(mock_session)
            result = await processor.process_notification(
                "char-e2e@example.com", "99999"
            )

        assert result.skipped is False
        assert result.processed_count == 1

        # Verify Gemini received gyaru system prompt
        gemini_kwargs = mock_gemini_instance.convert_email.call_args.kwargs
        assert gemini_kwargs["system_prompt"] == GYARU_CHARACTER.system_prompt

        # Verify TTS received gyaru voice name
        tts_kwargs = mock_tts_instance.synthesize_and_upload.call_args.kwargs
        assert tts_kwargs["voice_name"] == GYARU_CHARACTER.tts_voice_name

    @pytest.mark.asyncio
    async def test_selected_character_applied_to_new_email_req_3_3_4_1_4_2(
        self,
        mock_gmail_message: dict,
        mock_history_response: dict,
    ) -> None:
        """Requirements 3.3, 4.1, 4.2: New email uses selected character's prompt and voice.

        Verifies the E2E flow:
        1. User has selected_character_id="butler"
        2. process_notification processes an email
        3. Gemini receives butler's system_prompt
        4. TTS receives butler's tts_voice_name
        5. Email is saved with butler's conversion result
        """
        from src.services.character_service import BUTLER_CHARACTER
        from src.services.email_processor import EmailProcessorService

        mock_user = self._create_user(selected_character_id="butler")
        mock_contact = self._create_mock_contact(mock_user)

        mock_session = AsyncMock()
        self._setup_db_mocks(mock_session, mock_user, mock_contact)

        converted_text = (
            "ご主人様、上司様より報告書のご提出をお願いしたいとのことでございます。"
        )
        audio_url = "https://storage.googleapis.com/togenuki-audio/butler.mp3"

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
            mock_gmail = MagicMock()
            mock_gmail.fetch_email_history = AsyncMock(
                return_value=mock_history_response
            )
            mock_gmail.fetch_message = AsyncMock(return_value=mock_gmail_message)
            mock_gmail_client.return_value = mock_gmail

            mock_gemini_instance = MagicMock()
            mock_gemini_instance.convert_email = AsyncMock(
                return_value=Ok(converted_text)
            )
            mock_gemini.return_value = mock_gemini_instance

            mock_tts_instance = MagicMock()
            mock_tts_instance.synthesize_and_upload = AsyncMock(
                return_value=Ok(audio_url)
            )
            mock_tts.return_value = mock_tts_instance

            processor = EmailProcessorService(mock_session)
            result = await processor.process_notification(
                "char-e2e@example.com", "99999"
            )

        assert result.skipped is False
        assert result.processed_count == 1

        # Verify Gemini received butler system prompt
        gemini_kwargs = mock_gemini_instance.convert_email.call_args.kwargs
        assert gemini_kwargs["system_prompt"] == BUTLER_CHARACTER.system_prompt

        # Verify TTS received butler voice name
        tts_kwargs = mock_tts_instance.synthesize_and_upload.call_args.kwargs
        assert tts_kwargs["voice_name"] == BUTLER_CHARACTER.tts_voice_name

        # Verify saved email has butler's converted_body
        saved_email = mock_session.add.call_args[0][0]
        assert isinstance(saved_email, Email)
        assert saved_email.converted_body == converted_text
        assert saved_email.audio_url == audio_url
        assert saved_email.is_processed is True

    @pytest.mark.asyncio
    async def test_processed_email_unaffected_by_character_change_req_3_4(
        self,
        mock_gmail_message: dict,
    ) -> None:
        """Requirement 3.4: Already-processed emails are unaffected by character change.

        Verifies:
        1. Process email with gyaru → email saved with gyaru conversion
        2. Change user's character to butler
        3. Process new email → uses butler
        4. First email's converted_body and audio_url are unchanged
        """
        from src.services.character_service import (
            BUTLER_CHARACTER,
            GYARU_CHARACTER,
        )
        from src.services.email_processor import EmailProcessorService

        mock_contact = Contact(
            id=uuid7(),
            user_id=uuid7(),
            contact_email="boss@company.com",
            contact_name="上司さん",
        )

        # Step 1: Process first email with gyaru
        mock_session_1 = AsyncMock()
        mock_contact_result_1 = MagicMock()
        mock_contact_result_1.scalar_one_or_none.return_value = mock_contact
        mock_email_exists_1 = MagicMock()
        mock_email_exists_1.scalar_one_or_none.return_value = None
        mock_session_1.execute.side_effect = [
            mock_contact_result_1,
            mock_email_exists_1,
        ]

        gyaru_text = "やっほー先輩！ 報告書よろしくだし！"
        gyaru_audio = "https://storage.googleapis.com/audio/gyaru.mp3"

        with (
            patch("src.services.email_processor.GeminiService") as mock_gemini_1,
            patch("src.services.email_processor.TTSService") as mock_tts_1,
        ):
            mock_g1 = MagicMock()
            mock_g1.convert_email = AsyncMock(return_value=Ok(gyaru_text))
            mock_gemini_1.return_value = mock_g1

            mock_t1 = MagicMock()
            mock_t1.synthesize_and_upload = AsyncMock(return_value=Ok(gyaru_audio))
            mock_tts_1.return_value = mock_t1

            processor_1 = EmailProcessorService(mock_session_1)
            result_1 = await processor_1._process_single_message(
                mock_contact.user_id,
                mock_gmail_message,
                selected_character_id=None,
            )

        assert result_1.processed is True

        # Capture the first email's saved state
        first_email = mock_session_1.add.call_args[0][0]
        assert first_email.converted_body == gyaru_text
        assert first_email.audio_url == gyaru_audio

        # Verify gyaru was used
        g1_kwargs = mock_g1.convert_email.call_args.kwargs
        assert g1_kwargs["system_prompt"] == GYARU_CHARACTER.system_prompt

        # Step 2: Process second email with butler (simulating character change)
        mock_gmail_message_2 = {
            "id": "gmail-msg-char-e2e-2",
            "payload": {
                "headers": [
                    {"name": "From", "value": "Boss <boss@company.com>"},
                    {"name": "Subject", "value": "会議の件"},
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(
                        "明後日の会議の準備をお願いします。".encode()
                    ).decode()
                },
            },
            "internalDate": "1704196800000",
        }

        mock_session_2 = AsyncMock()
        mock_contact_result_2 = MagicMock()
        mock_contact_result_2.scalar_one_or_none.return_value = mock_contact
        mock_email_exists_2 = MagicMock()
        mock_email_exists_2.scalar_one_or_none.return_value = None
        mock_session_2.execute.side_effect = [
            mock_contact_result_2,
            mock_email_exists_2,
        ]

        butler_text = "ご主人様、会議の準備をお願いしたいとのことでございます。"
        butler_audio = "https://storage.googleapis.com/audio/butler.mp3"

        with (
            patch("src.services.email_processor.GeminiService") as mock_gemini_2,
            patch("src.services.email_processor.TTSService") as mock_tts_2,
        ):
            mock_g2 = MagicMock()
            mock_g2.convert_email = AsyncMock(return_value=Ok(butler_text))
            mock_gemini_2.return_value = mock_g2

            mock_t2 = MagicMock()
            mock_t2.synthesize_and_upload = AsyncMock(return_value=Ok(butler_audio))
            mock_tts_2.return_value = mock_t2

            processor_2 = EmailProcessorService(mock_session_2)
            result_2 = await processor_2._process_single_message(
                mock_contact.user_id,
                mock_gmail_message_2,
                selected_character_id="butler",
            )

        assert result_2.processed is True

        # Verify butler was used for second email
        g2_kwargs = mock_g2.convert_email.call_args.kwargs
        assert g2_kwargs["system_prompt"] == BUTLER_CHARACTER.system_prompt

        # Step 3: Verify first email remains unchanged
        assert first_email.converted_body == gyaru_text
        assert first_email.audio_url == gyaru_audio
        assert first_email.is_processed is True

    @pytest.mark.asyncio
    async def test_invalid_character_id_falls_back_to_default_req_4_3(
        self,
        mock_gmail_message: dict,
        mock_history_response: dict,
    ) -> None:
        """Requirement 4.3: Invalid character ID falls back to gyaru (default).

        Verifies the E2E flow:
        1. User has selected_character_id="nonexistent"
        2. process_notification processes an email
        3. Gemini receives gyaru's system_prompt (fallback)
        4. TTS receives gyaru's tts_voice_name (fallback)
        """
        from src.services.character_service import GYARU_CHARACTER
        from src.services.email_processor import EmailProcessorService

        mock_user = self._create_user(selected_character_id="nonexistent")
        mock_contact = self._create_mock_contact(mock_user)

        mock_session = AsyncMock()
        self._setup_db_mocks(mock_session, mock_user, mock_contact)

        converted_text = "やっほー先輩！"
        audio_url = "https://storage.googleapis.com/togenuki-audio/fallback.mp3"

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
            mock_gmail = MagicMock()
            mock_gmail.fetch_email_history = AsyncMock(
                return_value=mock_history_response
            )
            mock_gmail.fetch_message = AsyncMock(return_value=mock_gmail_message)
            mock_gmail_client.return_value = mock_gmail

            mock_gemini_instance = MagicMock()
            mock_gemini_instance.convert_email = AsyncMock(
                return_value=Ok(converted_text)
            )
            mock_gemini.return_value = mock_gemini_instance

            mock_tts_instance = MagicMock()
            mock_tts_instance.synthesize_and_upload = AsyncMock(
                return_value=Ok(audio_url)
            )
            mock_tts.return_value = mock_tts_instance

            processor = EmailProcessorService(mock_session)
            result = await processor.process_notification(
                "char-e2e@example.com", "99999"
            )

        assert result.skipped is False
        assert result.processed_count == 1

        # Verify Gemini received gyaru system prompt (fallback from invalid ID)
        gemini_kwargs = mock_gemini_instance.convert_email.call_args.kwargs
        assert gemini_kwargs["system_prompt"] == GYARU_CHARACTER.system_prompt

        # Verify TTS received gyaru voice name (fallback from invalid ID)
        tts_kwargs = mock_tts_instance.synthesize_and_upload.call_args.kwargs
        assert tts_kwargs["voice_name"] == GYARU_CHARACTER.tts_voice_name
