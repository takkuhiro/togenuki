"""Tests for ReplySyncService (Gmail reply detection).

Tests for the reply sync service that detects when users reply
directly via Gmail and updates the email status accordingly.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from uuid6 import uuid7

from src.models import Email, User


@pytest.fixture
def mock_session() -> AsyncMock:
    """Create a mock async database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_user() -> User:
    """Create a mock user with Gmail OAuth tokens."""
    return User(
        id=uuid7(),
        firebase_uid="test-uid-123",
        email="user@example.com",
        gmail_refresh_token="refresh-token-123",
        gmail_access_token="access-token-123",
        gmail_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )


def make_email(
    user_id,
    *,
    google_thread_id=None,
    received_at=None,
    replied_at=None,
    reply_source=None,
) -> Email:
    """Helper to create an Email with specific fields."""
    return Email(
        id=uuid7(),
        user_id=user_id,
        google_message_id=f"msg-{uuid7()}",
        google_thread_id=google_thread_id,
        sender_email="boss@company.com",
        sender_name="Boss",
        subject="Test Subject",
        original_body="Test body",
        received_at=received_at or datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        is_processed=True,
        replied_at=replied_at,
        reply_source=reply_source,
    )


def make_thread_response(thread_id: str, messages: list[dict]) -> dict:
    """Helper to create a Gmail threads.get response."""
    return {
        "id": thread_id,
        "messages": messages,
    }


def make_thread_message(
    msg_id: str,
    internal_date_ms: str,
    label_ids: list[str],
) -> dict:
    """Helper to create a message within a thread response."""
    return {
        "id": msg_id,
        "internalDate": internal_date_ms,
        "labelIds": label_ids,
        "payload": {"headers": []},
    }


class TestReplySyncService:
    """Tests for ReplySyncService.sync_reply_status method."""

    @pytest.mark.asyncio
    async def test_sync_detects_gmail_reply_after_received_email(
        self,
        mock_session: AsyncMock,
        mock_user: User,
    ):
        """When a SENT message exists after received_at, mark as gmail reply."""
        from src.services.reply_sync_service import ReplySyncService

        # 1704067200 = 2024-01-01 00:00:00 UTC
        received_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
        email = make_email(
            mock_user.id,
            google_thread_id="thread-1",
            received_at=received_time,
        )

        # Thread: incoming at 00:00, SENT at 00:30 (after received)
        thread_response = make_thread_response(
            "thread-1",
            [
                make_thread_message("msg-recv", "1704067200000", ["INBOX"]),
                make_thread_message("msg-sent", "1704069000000", ["SENT"]),
            ],
        )

        mock_gmail_client = MagicMock()
        mock_gmail_client.fetch_thread = AsyncMock(return_value=thread_response)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [email]
        mock_session.execute.return_value = mock_result

        service = ReplySyncService()
        count = await service.sync_reply_status(
            mock_session, mock_user, mock_gmail_client
        )

        assert count == 1
        assert email.replied_at is not None
        assert email.reply_source == "gmail"

    @pytest.mark.asyncio
    async def test_sync_does_not_mark_when_no_sent_after_received(
        self,
        mock_session: AsyncMock,
        mock_user: User,
    ):
        """When no SENT message exists after received_at, email stays unreplied."""
        from src.services.reply_sync_service import ReplySyncService

        # 1704070800 = 2024-01-01 01:00:00 UTC — received AFTER the SENT
        received_time = datetime(2024, 1, 1, 1, 0, tzinfo=timezone.utc)
        email = make_email(
            mock_user.id,
            google_thread_id="thread-1",
            received_at=received_time,
        )

        # Thread: SENT at 00:30, incoming at 01:00
        thread_response = make_thread_response(
            "thread-1",
            [
                make_thread_message("msg-sent", "1704069000000", ["SENT"]),
                make_thread_message("msg-recv", "1704070800000", ["INBOX"]),
            ],
        )

        mock_gmail_client = MagicMock()
        mock_gmail_client.fetch_thread = AsyncMock(return_value=thread_response)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [email]
        mock_session.execute.return_value = mock_result

        service = ReplySyncService()
        count = await service.sync_reply_status(
            mock_session, mock_user, mock_gmail_client
        )

        assert count == 0
        assert email.replied_at is None
        assert email.reply_source is None

    @pytest.mark.asyncio
    async def test_sync_handles_multi_turn_conversation_correctly(
        self,
        mock_session: AsyncMock,
        mock_user: User,
    ):
        """In a multi-turn thread, only emails with a later SENT are marked replied."""
        from src.services.reply_sync_service import ReplySyncService

        # Email 1: received at 00:00 — has SENT at 00:30 → replied
        email1 = make_email(
            mock_user.id,
            google_thread_id="thread-1",
            received_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        )
        # Email 2: received at 01:00 — no SENT after 01:00 → unreplied
        email2 = make_email(
            mock_user.id,
            google_thread_id="thread-1",
            received_at=datetime(2024, 1, 1, 1, 0, tzinfo=timezone.utc),
        )

        # 1704067200 = 00:00, 1704069000 = 00:30, 1704070800 = 01:00
        thread_response = make_thread_response(
            "thread-1",
            [
                make_thread_message("msg-1", "1704067200000", ["INBOX"]),
                make_thread_message("msg-2", "1704069000000", ["SENT"]),
                make_thread_message("msg-3", "1704070800000", ["INBOX"]),
            ],
        )

        mock_gmail_client = MagicMock()
        mock_gmail_client.fetch_thread = AsyncMock(return_value=thread_response)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [email1, email2]
        mock_session.execute.return_value = mock_result

        service = ReplySyncService()
        count = await service.sync_reply_status(
            mock_session, mock_user, mock_gmail_client
        )

        assert count == 1
        assert email1.replied_at is not None
        assert email1.reply_source == "gmail"
        assert email2.replied_at is None
        assert email2.reply_source is None

    @pytest.mark.asyncio
    async def test_sync_returns_zero_when_no_unreplied_emails(
        self,
        mock_session: AsyncMock,
        mock_user: User,
    ):
        """When there are no unreplied emails, sync should return 0."""
        from src.services.reply_sync_service import ReplySyncService

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        mock_gmail_client = MagicMock()

        service = ReplySyncService()
        count = await service.sync_reply_status(
            mock_session, mock_user, mock_gmail_client
        )

        assert count == 0
        mock_gmail_client.fetch_thread.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_fetches_thread_id_for_emails_without_one(
        self,
        mock_session: AsyncMock,
        mock_user: User,
    ):
        """Emails without google_thread_id should have it fetched and stored."""
        from src.services.reply_sync_service import ReplySyncService

        email = make_email(
            mock_user.id,
            google_thread_id=None,
            received_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        )

        mock_gmail_client = MagicMock()
        mock_gmail_client.fetch_message = AsyncMock(
            return_value={"id": email.google_message_id, "threadId": "thread-new"}
        )
        thread_response = make_thread_response(
            "thread-new",
            [
                make_thread_message("msg-1", "1704067200000", ["INBOX"]),
                make_thread_message("msg-2", "1704069000000", ["SENT"]),
            ],
        )
        mock_gmail_client.fetch_thread = AsyncMock(return_value=thread_response)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [email]
        mock_session.execute.return_value = mock_result

        service = ReplySyncService()
        count = await service.sync_reply_status(
            mock_session, mock_user, mock_gmail_client
        )

        assert email.google_thread_id == "thread-new"
        assert count == 1

    @pytest.mark.asyncio
    async def test_sync_groups_emails_by_thread_id(
        self,
        mock_session: AsyncMock,
        mock_user: User,
    ):
        """Multiple emails in same thread should only trigger one API call."""
        from src.services.reply_sync_service import ReplySyncService

        email1 = make_email(
            mock_user.id,
            google_thread_id="thread-1",
            received_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        )
        email2 = make_email(
            mock_user.id,
            google_thread_id="thread-1",
            received_at=datetime(2024, 1, 1, 1, 0, tzinfo=timezone.utc),
        )

        thread_response = make_thread_response(
            "thread-1",
            [
                make_thread_message("msg-1", "1704067200000", ["INBOX"]),
                make_thread_message("msg-2", "1704069000000", ["SENT"]),
                make_thread_message("msg-3", "1704070800000", ["INBOX"]),
            ],
        )

        mock_gmail_client = MagicMock()
        mock_gmail_client.fetch_thread = AsyncMock(return_value=thread_response)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [email1, email2]
        mock_session.execute.return_value = mock_result

        service = ReplySyncService()
        await service.sync_reply_status(mock_session, mock_user, mock_gmail_client)

        # Only one fetch_thread call for the same thread
        mock_gmail_client.fetch_thread.assert_called_once_with("thread-1")
