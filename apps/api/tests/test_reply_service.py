"""Tests for ReplyService (Reply Orchestration).

Tests for the reply orchestration service that handles:
- compose_reply: Email fetch -> contact_context -> Gemini composition -> subject generation
- send_reply: OAuth token refresh -> Gmail send -> DB update
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from src.auth.schemas import FirebaseUser
from src.models import Contact, ContactContext, Email, User


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_user() -> User:
    """Create a mock user with Gmail OAuth tokens."""
    user = User(
        id=uuid7(),
        firebase_uid="test-uid-123",
        email="user@example.com",
        gmail_refresh_token="refresh-token-123",
        gmail_access_token="access-token-123",
        gmail_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    return user


@pytest.fixture
def firebase_user() -> FirebaseUser:
    """Create a Firebase authenticated user."""
    return FirebaseUser(uid="test-uid-123", email="user@example.com")


@pytest.fixture
def mock_email(mock_user: User) -> Email:
    """Create a mock email record."""
    return Email(
        id=uuid7(),
        user_id=mock_user.id,
        contact_id=uuid7(),
        google_message_id="msg-123",
        sender_email="boss@company.com",
        sender_name="Boss",
        subject="報告書について",
        original_body="明日までに報告書を提出してください。",
        is_processed=True,
    )


@pytest.fixture
def mock_contact(mock_user: User, mock_email: Email) -> Contact:
    """Create a mock contact with context."""
    contact = Contact(
        id=mock_email.contact_id,
        user_id=mock_user.id,
        contact_email="boss@company.com",
        contact_name="Boss",
        is_learning_complete=True,
    )
    return contact


@pytest.fixture
def mock_contact_context(mock_contact: Contact) -> ContactContext:
    """Create a mock contact context."""
    return ContactContext(
        id=uuid7(),
        contact_id=mock_contact.id,
        learned_patterns='{"contactCharacteristics": {"tone": "formal"}}',
    )


class TestComposeReply:
    """Tests for ReplyService.compose_reply method."""

    @pytest.mark.asyncio
    async def test_compose_reply_returns_composed_text_and_subject(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_email: Email,
        mock_contact: Contact,
        mock_contact_context: ContactContext,
    ):
        """compose_reply should return composed business email and subject."""
        from result import Ok

        from src.services.reply_service import ReplyService

        # Mock dependencies
        mock_contact.context = mock_contact_context

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
            patch(
                "src.services.reply_service.get_contact_for_email",
                new_callable=AsyncMock,
                return_value=mock_contact,
            ),
        ):
            mock_gemini = MagicMock()
            mock_gemini.compose_business_reply = AsyncMock(
                return_value=Ok("お疲れ様です。報告書の件、承知いたしました。")
            )

            service = ReplyService(gemini_service=mock_gemini)
            result = await service.compose_reply(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                raw_text="了解っす、明日出します",
            )

            assert result.is_ok()
            reply_result = result.unwrap()
            assert (
                reply_result.composed_body
                == "お疲れ様です。報告書の件、承知いたしました。"
            )
            assert reply_result.composed_subject == "Re: 報告書について"

    @pytest.mark.asyncio
    async def test_compose_reply_generates_subject_with_re_prefix(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_email: Email,
        mock_contact: Contact,
    ):
        """compose_reply should prefix subject with 'Re: ' when not already present."""
        from result import Ok

        from src.services.reply_service import ReplyService

        mock_email.subject = "会議のお知らせ"

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
            patch(
                "src.services.reply_service.get_contact_for_email",
                new_callable=AsyncMock,
                return_value=mock_contact,
            ),
        ):
            mock_gemini = MagicMock()
            mock_gemini.compose_business_reply = AsyncMock(
                return_value=Ok("清書されたメール")
            )

            service = ReplyService(gemini_service=mock_gemini)
            result = await service.compose_reply(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                raw_text="了解です",
            )

            assert result.is_ok()
            assert result.unwrap().composed_subject == "Re: 会議のお知らせ"

    @pytest.mark.asyncio
    async def test_compose_reply_does_not_double_re_prefix(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_email: Email,
        mock_contact: Contact,
    ):
        """compose_reply should not add 'Re: ' if subject already starts with it."""
        from result import Ok

        from src.services.reply_service import ReplyService

        mock_email.subject = "Re: 報告書について"

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
            patch(
                "src.services.reply_service.get_contact_for_email",
                new_callable=AsyncMock,
                return_value=mock_contact,
            ),
        ):
            mock_gemini = MagicMock()
            mock_gemini.compose_business_reply = AsyncMock(
                return_value=Ok("清書されたメール")
            )

            service = ReplyService(gemini_service=mock_gemini)
            result = await service.compose_reply(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                raw_text="了解です",
            )

            assert result.is_ok()
            assert result.unwrap().composed_subject == "Re: 報告書について"

    @pytest.mark.asyncio
    async def test_compose_reply_passes_contact_context_to_gemini(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_email: Email,
        mock_contact: Contact,
        mock_contact_context: ContactContext,
    ):
        """compose_reply should pass contact_context to Gemini when available."""
        from result import Ok

        from src.services.reply_service import ReplyService

        mock_contact.context = mock_contact_context

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
            patch(
                "src.services.reply_service.get_contact_for_email",
                new_callable=AsyncMock,
                return_value=mock_contact,
            ),
        ):
            mock_gemini = MagicMock()
            mock_gemini.compose_business_reply = AsyncMock(
                return_value=Ok("清書されたメール")
            )

            service = ReplyService(gemini_service=mock_gemini)
            await service.compose_reply(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                raw_text="了解です",
            )

            mock_gemini.compose_business_reply.assert_called_once()
            call_kwargs = mock_gemini.compose_business_reply.call_args
            assert '{"contactCharacteristics"' in str(call_kwargs)

    @pytest.mark.asyncio
    async def test_compose_reply_email_not_found_returns_error(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
    ):
        """compose_reply should return EMAIL_NOT_FOUND when email doesn't exist."""
        from src.services.reply_service import ReplyError, ReplyService

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            mock_gemini = MagicMock()
            service = ReplyService(gemini_service=mock_gemini)
            result = await service.compose_reply(
                session=mock_session,
                user=firebase_user,
                email_id=uuid7(),
                raw_text="了解です",
            )

            assert result.is_err()
            assert result.unwrap_err() == ReplyError.EMAIL_NOT_FOUND

    @pytest.mark.asyncio
    async def test_compose_reply_unauthorized_returns_error(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_email: Email,
    ):
        """compose_reply should return UNAUTHORIZED when email belongs to another user."""
        from src.services.reply_service import ReplyError, ReplyService

        # Create a different user
        other_user = User(
            id=uuid7(),
            firebase_uid="test-uid-123",
            email="user@example.com",
        )

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=other_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
        ):
            mock_gemini = MagicMock()
            service = ReplyService(gemini_service=mock_gemini)
            result = await service.compose_reply(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                raw_text="了解です",
            )

            assert result.is_err()
            assert result.unwrap_err() == ReplyError.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_compose_reply_gemini_failure_returns_error(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_email: Email,
        mock_contact: Contact,
    ):
        """compose_reply should return COMPOSE_FAILED when Gemini fails."""
        from result import Err

        from src.services.gemini_service import GeminiError
        from src.services.reply_service import ReplyError, ReplyService

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
            patch(
                "src.services.reply_service.get_contact_for_email",
                new_callable=AsyncMock,
                return_value=mock_contact,
            ),
        ):
            mock_gemini = MagicMock()
            mock_gemini.compose_business_reply = AsyncMock(
                return_value=Err(GeminiError.API_ERROR)
            )

            service = ReplyService(gemini_service=mock_gemini)
            result = await service.compose_reply(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                raw_text="了解です",
            )

            assert result.is_err()
            assert result.unwrap_err() == ReplyError.COMPOSE_FAILED

    @pytest.mark.asyncio
    async def test_compose_reply_user_not_found_returns_error(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
    ):
        """compose_reply should return UNAUTHORIZED when user is not found in DB."""
        from src.services.reply_service import ReplyError, ReplyService

        with patch(
            "src.services.reply_service.get_user_by_firebase_uid",
            new_callable=AsyncMock,
            return_value=None,
        ):
            mock_gemini = MagicMock()
            service = ReplyService(gemini_service=mock_gemini)
            result = await service.compose_reply(
                session=mock_session,
                user=firebase_user,
                email_id=uuid7(),
                raw_text="了解です",
            )

            assert result.is_err()
            assert result.unwrap_err() == ReplyError.UNAUTHORIZED


class TestSendReply:
    """Tests for ReplyService.send_reply method."""

    @pytest.mark.asyncio
    async def test_send_reply_sends_email_and_updates_db(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_email: Email,
    ):
        """send_reply should send email via Gmail and update DB record."""
        from src.services.reply_service import ReplyService

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
        ):
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(
                return_value={
                    "access_token": "valid-access-token",
                    "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
                }
            )

            mock_gmail_client_class = MagicMock()
            mock_gmail_client = MagicMock()
            mock_gmail_client.send_message = AsyncMock(
                return_value={
                    "id": "sent-msg-456",
                    "threadId": "thread-abc",
                    "labelIds": ["SENT"],
                }
            )
            mock_gmail_client.fetch_message = AsyncMock(
                return_value={
                    "id": "msg-123",
                    "threadId": "thread-abc",
                    "payload": {
                        "headers": [
                            {
                                "name": "Message-ID",
                                "value": "<original-msg@mail.gmail.com>",
                            },
                        ],
                    },
                }
            )
            mock_gmail_client_class.return_value = mock_gmail_client

            mock_gemini = MagicMock()
            service = ReplyService(
                gemini_service=mock_gemini,
                oauth_service=mock_oauth,
                gmail_client_class=mock_gmail_client_class,
            )
            result = await service.send_reply(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                composed_body="お疲れ様です。報告書の件、承知いたしました。",
                composed_subject="Re: 報告書について",
            )

            assert result.is_ok()
            send_result = result.unwrap()
            assert send_result.google_message_id == "sent-msg-456"

            # Verify DB update
            assert (
                mock_email.reply_body == "お疲れ様です。報告書の件、承知いたしました。"
            )
            assert mock_email.reply_subject == "Re: 報告書について"
            assert mock_email.replied_at is not None
            assert mock_email.reply_google_message_id == "sent-msg-456"
            assert mock_email.reply_source == "togenuki"

            # session.commit() が呼ばれたことを検証
            mock_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_send_reply_refreshes_expired_token(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_email: Email,
    ):
        """send_reply should refresh OAuth token when expired."""
        from src.services.reply_service import ReplyService

        mock_user.gmail_token_expires_at = datetime.now(timezone.utc) - timedelta(
            hours=1
        )

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
        ):
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(
                return_value={
                    "access_token": "new-refreshed-token",
                    "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
                }
            )

            mock_gmail_client = MagicMock()
            mock_gmail_client.send_message = AsyncMock(
                return_value={
                    "id": "sent-msg-456",
                    "threadId": "thread-abc",
                    "labelIds": ["SENT"],
                }
            )
            mock_gmail_client.fetch_message = AsyncMock(
                return_value={
                    "id": "msg-123",
                    "threadId": "thread-abc",
                    "payload": {
                        "headers": [
                            {
                                "name": "Message-ID",
                                "value": "<original-msg@mail.gmail.com>",
                            },
                        ],
                    },
                }
            )
            mock_gmail_client_class = MagicMock(return_value=mock_gmail_client)

            mock_gemini = MagicMock()
            service = ReplyService(
                gemini_service=mock_gemini,
                oauth_service=mock_oauth,
                gmail_client_class=mock_gmail_client_class,
            )
            result = await service.send_reply(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                composed_body="返信メール",
                composed_subject="Re: テスト",
            )

            assert result.is_ok()
            mock_oauth.ensure_valid_access_token.assert_called_once_with(
                current_token=mock_user.gmail_access_token,
                expires_at=mock_user.gmail_token_expires_at,
                refresh_token=mock_user.gmail_refresh_token,
            )

    @pytest.mark.asyncio
    async def test_send_reply_token_refresh_failure_returns_error(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_email: Email,
    ):
        """send_reply should return TOKEN_EXPIRED when token refresh fails."""
        from src.services.reply_service import ReplyError, ReplyService

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
        ):
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(return_value=None)

            mock_gemini = MagicMock()
            service = ReplyService(
                gemini_service=mock_gemini,
                oauth_service=mock_oauth,
            )
            result = await service.send_reply(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                composed_body="返信メール",
                composed_subject="Re: テスト",
            )

            assert result.is_err()
            assert result.unwrap_err() == ReplyError.TOKEN_EXPIRED

    @pytest.mark.asyncio
    async def test_send_reply_gmail_failure_returns_error(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_email: Email,
    ):
        """send_reply should return SEND_FAILED when Gmail API fails."""
        from src.services.gmail_service import GmailApiError
        from src.services.reply_service import ReplyError, ReplyService

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
        ):
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(
                return_value={
                    "access_token": "valid-token",
                    "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
                }
            )

            mock_gmail_client = MagicMock()
            mock_gmail_client.send_message = AsyncMock(
                side_effect=GmailApiError("Failed to send", status_code=500)
            )
            mock_gmail_client.fetch_message = AsyncMock(
                return_value={
                    "id": "msg-123",
                    "threadId": "thread-abc",
                    "payload": {
                        "headers": [
                            {
                                "name": "Message-ID",
                                "value": "<original-msg@mail.gmail.com>",
                            },
                        ],
                    },
                }
            )
            mock_gmail_client_class = MagicMock(return_value=mock_gmail_client)

            mock_gemini = MagicMock()
            service = ReplyService(
                gemini_service=mock_gemini,
                oauth_service=mock_oauth,
                gmail_client_class=mock_gmail_client_class,
            )
            result = await service.send_reply(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                composed_body="返信メール",
                composed_subject="Re: テスト",
            )

            assert result.is_err()
            assert result.unwrap_err() == ReplyError.SEND_FAILED

    @pytest.mark.asyncio
    async def test_send_reply_email_not_found_returns_error(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
    ):
        """send_reply should return EMAIL_NOT_FOUND when email doesn't exist."""
        from src.services.reply_service import ReplyError, ReplyService

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            mock_gemini = MagicMock()
            service = ReplyService(gemini_service=mock_gemini)
            result = await service.send_reply(
                session=mock_session,
                user=firebase_user,
                email_id=uuid7(),
                composed_body="返信メール",
                composed_subject="Re: テスト",
            )

            assert result.is_err()
            assert result.unwrap_err() == ReplyError.EMAIL_NOT_FOUND

    @pytest.mark.asyncio
    async def test_send_reply_already_replied_returns_error(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_email: Email,
    ):
        """send_reply should return ALREADY_REPLIED when email has been replied to."""
        from src.services.reply_service import ReplyError, ReplyService

        mock_email.replied_at = datetime.now(timezone.utc)

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
        ):
            mock_gemini = MagicMock()
            service = ReplyService(gemini_service=mock_gemini)
            result = await service.send_reply(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                composed_body="返信メール",
                composed_subject="Re: テスト",
            )

            assert result.is_err()
            assert result.unwrap_err() == ReplyError.ALREADY_REPLIED


class TestSaveDraft:
    """Tests for ReplyService.save_draft method."""

    @pytest.mark.asyncio
    async def test_save_draft_success(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_email: Email,
    ):
        """save_draft should create draft via Gmail and return draft ID."""
        from src.services.reply_service import ReplyService

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
        ):
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(
                return_value={
                    "access_token": "valid-access-token",
                    "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
                }
            )

            mock_gmail_client_class = MagicMock()
            mock_gmail_client = MagicMock()
            mock_gmail_client.create_draft = AsyncMock(
                return_value={
                    "id": "draft-789",
                    "message": {
                        "id": "msg-draft-456",
                        "threadId": "thread-abc",
                        "labelIds": ["DRAFT"],
                    },
                }
            )
            mock_gmail_client.fetch_message = AsyncMock(
                return_value={
                    "id": "msg-123",
                    "threadId": "thread-abc",
                    "payload": {
                        "headers": [
                            {
                                "name": "Message-ID",
                                "value": "<original-msg@mail.gmail.com>",
                            },
                        ],
                    },
                }
            )
            mock_gmail_client_class.return_value = mock_gmail_client

            mock_gemini = MagicMock()
            service = ReplyService(
                gemini_service=mock_gemini,
                oauth_service=mock_oauth,
                gmail_client_class=mock_gmail_client_class,
            )
            result = await service.save_draft(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                composed_body="お疲れ様です。報告書の件、承知いたしました。",
                composed_subject="Re: 報告書について",
            )

            assert result.is_ok()
            draft_result = result.unwrap()
            assert draft_result.google_draft_id == "draft-789"

            # DB should NOT be updated for drafts
            mock_session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_save_draft_email_not_found(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
    ):
        """save_draft should return EMAIL_NOT_FOUND when email doesn't exist."""
        from src.services.reply_service import ReplyError, ReplyService

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
        ):
            mock_gemini = MagicMock()
            service = ReplyService(gemini_service=mock_gemini)
            result = await service.save_draft(
                session=mock_session,
                user=firebase_user,
                email_id=uuid7(),
                composed_body="返信メール",
                composed_subject="Re: テスト",
            )

            assert result.is_err()
            assert result.unwrap_err() == ReplyError.EMAIL_NOT_FOUND

    @pytest.mark.asyncio
    async def test_save_draft_unauthorized(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_email: Email,
    ):
        """save_draft should return UNAUTHORIZED when email belongs to another user."""
        from src.services.reply_service import ReplyError, ReplyService

        other_user = User(
            id=uuid7(),
            firebase_uid="test-uid-123",
            email="user@example.com",
        )

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=other_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
        ):
            mock_gemini = MagicMock()
            service = ReplyService(gemini_service=mock_gemini)
            result = await service.save_draft(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                composed_body="返信メール",
                composed_subject="Re: テスト",
            )

            assert result.is_err()
            assert result.unwrap_err() == ReplyError.UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_save_draft_token_expired(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_email: Email,
    ):
        """save_draft should return TOKEN_EXPIRED when token refresh fails."""
        from src.services.reply_service import ReplyError, ReplyService

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
        ):
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(return_value=None)

            mock_gemini = MagicMock()
            service = ReplyService(
                gemini_service=mock_gemini,
                oauth_service=mock_oauth,
            )
            result = await service.save_draft(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                composed_body="返信メール",
                composed_subject="Re: テスト",
            )

            assert result.is_err()
            assert result.unwrap_err() == ReplyError.TOKEN_EXPIRED

    @pytest.mark.asyncio
    async def test_save_draft_gmail_api_error(
        self,
        mock_session: AsyncMock,
        firebase_user: FirebaseUser,
        mock_user: User,
        mock_email: Email,
    ):
        """save_draft should return DRAFT_FAILED when Gmail API fails."""
        from src.services.gmail_service import GmailApiError
        from src.services.reply_service import ReplyError, ReplyService

        with (
            patch(
                "src.services.reply_service.get_user_by_firebase_uid",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch(
                "src.services.reply_service.get_email_by_id",
                new_callable=AsyncMock,
                return_value=mock_email,
            ),
        ):
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(
                return_value={
                    "access_token": "valid-token",
                    "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
                }
            )

            mock_gmail_client = MagicMock()
            mock_gmail_client.create_draft = AsyncMock(
                side_effect=GmailApiError("Failed to create draft", status_code=500)
            )
            mock_gmail_client.fetch_message = AsyncMock(
                return_value={
                    "id": "msg-123",
                    "threadId": "thread-abc",
                    "payload": {
                        "headers": [
                            {
                                "name": "Message-ID",
                                "value": "<original-msg@mail.gmail.com>",
                            },
                        ],
                    },
                }
            )
            mock_gmail_client_class = MagicMock(return_value=mock_gmail_client)

            mock_gemini = MagicMock()
            service = ReplyService(
                gemini_service=mock_gemini,
                oauth_service=mock_oauth,
                gmail_client_class=mock_gmail_client_class,
            )
            result = await service.save_draft(
                session=mock_session,
                user=firebase_user,
                email_id=mock_email.id,
                composed_body="返信メール",
                composed_subject="Re: テスト",
            )

            assert result.is_err()
            assert result.unwrap_err() == ReplyError.DRAFT_FAILED
