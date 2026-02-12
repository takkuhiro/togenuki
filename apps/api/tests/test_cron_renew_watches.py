"""Tests for cron endpoint: renew Gmail watches.

Cloud Scheduler calls POST /api/cron/renew-gmail-watches every 6 days
to renew Gmail Watch for all connected users.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from uuid6 import uuid7

from src.models import User

TEST_SCHEDULER_SECRET = "test-scheduler-secret"


class TestCronAuthentication:
    """Tests for X-Scheduler-Secret header authentication (integration tests)."""

    async def _make_request(self, headers: dict | None = None):
        """Make a POST request to the renew-gmail-watches endpoint via ASGI."""
        from src.database import get_db
        from src.main import app

        async def mock_get_db():
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []
            mock_session.execute.return_value = mock_result
            yield mock_session

        app.dependency_overrides[get_db] = mock_get_db
        try:
            with patch("src.routers.cron.get_settings") as mock_get_settings:
                mock_settings_obj = MagicMock()
                mock_settings_obj.scheduler_secret = TEST_SCHEDULER_SECRET
                mock_get_settings.return_value = mock_settings_obj

                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app),
                    base_url="http://test",
                ) as client:
                    return await client.post(
                        "/api/cron/renew-gmail-watches",
                        headers=headers or {},
                    )
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_missing_secret_returns_403(self):
        """Request without X-Scheduler-Secret header returns 403."""
        response = await self._make_request()
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_wrong_secret_returns_403(self):
        """Request with wrong X-Scheduler-Secret returns 403."""
        response = await self._make_request(
            headers={"X-Scheduler-Secret": "wrong-secret"}
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_correct_secret_returns_200(self):
        """Request with correct X-Scheduler-Secret returns 200."""
        response = await self._make_request(
            headers={"X-Scheduler-Secret": TEST_SCHEDULER_SECRET}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["succeeded"] == 0
        assert data["failed"] == 0


class TestRenewGmailWatches:
    """Tests for renew Gmail watches business logic (direct function call)."""

    @pytest.fixture
    def mock_users(self) -> list[User]:
        """Create mock users with Gmail OAuth tokens."""
        return [
            User(
                id=uuid7(),
                firebase_uid="uid-1",
                email="user1@example.com",
                gmail_refresh_token="refresh-1",
                gmail_access_token="access-1",
                gmail_token_expires_at=datetime.now(timezone.utc),
                gmail_history_id="history-100",
            ),
            User(
                id=uuid7(),
                firebase_uid="uid-2",
                email="user2@example.com",
                gmail_refresh_token="refresh-2",
                gmail_access_token="access-2",
                gmail_token_expires_at=datetime.now(timezone.utc),
                gmail_history_id="history-200",
            ),
        ]

    def _mock_session_with_users(self, users: list[User]) -> AsyncMock:
        """Create a mock async session that returns the given users from query."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = users
        session.execute.return_value = mock_result
        return session

    @pytest.mark.asyncio
    async def test_watches_renewed_for_connected_users(self, mock_users):
        """Gmail watches are renewed for all connected users."""
        from src.routers.cron import renew_gmail_watches
        from src.services.gmail_watch import GmailWatchResult

        session = self._mock_session_with_users(mock_users)

        with (
            patch("src.routers.cron.GmailOAuthService") as mock_oauth_class,
            patch("src.routers.cron.GmailWatchService") as mock_watch_class,
        ):
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(
                return_value={
                    "access_token": "access-1",
                    "expires_at": datetime.now(timezone.utc),
                }
            )
            mock_oauth_class.return_value = mock_oauth

            mock_watch = MagicMock()
            mock_watch.setup_watch = AsyncMock(
                return_value=GmailWatchResult(
                    success=True,
                    history_id="new-history-999",
                    expiration=datetime.now(timezone.utc),
                )
            )
            mock_watch_class.return_value = mock_watch

            response = await renew_gmail_watches(session=session)

        assert response.total == 2
        assert response.succeeded == 2
        assert response.failed == 0
        assert mock_watch.setup_watch.call_count == 2

    @pytest.mark.asyncio
    async def test_history_id_not_updated(self, mock_users):
        """gmail_history_id must NOT be updated during watch renewal."""
        from src.routers.cron import renew_gmail_watches
        from src.services.gmail_watch import GmailWatchResult

        original_history_ids = [u.gmail_history_id for u in mock_users]
        session = self._mock_session_with_users(mock_users)

        with (
            patch("src.routers.cron.GmailOAuthService") as mock_oauth_class,
            patch("src.routers.cron.GmailWatchService") as mock_watch_class,
        ):
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(
                return_value={
                    "access_token": "access-1",
                    "expires_at": datetime.now(timezone.utc),
                }
            )
            mock_oauth_class.return_value = mock_oauth

            mock_watch = MagicMock()
            mock_watch.setup_watch = AsyncMock(
                return_value=GmailWatchResult(
                    success=True,
                    history_id="new-history-999",
                    expiration=datetime.now(timezone.utc),
                )
            )
            mock_watch_class.return_value = mock_watch

            await renew_gmail_watches(session=session)

        for user, original_id in zip(mock_users, original_history_ids, strict=True):
            assert user.gmail_history_id == original_id

    @pytest.mark.asyncio
    async def test_token_refresh_updates_db(self, mock_users):
        """When token is refreshed, access_token and expires_at are updated."""
        from src.routers.cron import renew_gmail_watches
        from src.services.gmail_watch import GmailWatchResult

        user = mock_users[0]
        session = self._mock_session_with_users([user])
        new_expires_at = datetime(2025, 12, 31, tzinfo=timezone.utc)

        with (
            patch("src.routers.cron.GmailOAuthService") as mock_oauth_class,
            patch("src.routers.cron.GmailWatchService") as mock_watch_class,
        ):
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(
                return_value={
                    "access_token": "new-access-token",
                    "expires_at": new_expires_at,
                }
            )
            mock_oauth_class.return_value = mock_oauth

            mock_watch = MagicMock()
            mock_watch.setup_watch = AsyncMock(
                return_value=GmailWatchResult(
                    success=True,
                    history_id="h-123",
                    expiration=datetime.now(timezone.utc),
                )
            )
            mock_watch_class.return_value = mock_watch

            await renew_gmail_watches(session=session)

        assert user.gmail_access_token == "new-access-token"
        assert user.gmail_token_expires_at == new_expires_at
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_one_user_failure_does_not_stop_others(self, mock_users):
        """When one user fails, other users are still processed."""
        from src.routers.cron import renew_gmail_watches
        from src.services.gmail_watch import GmailWatchResult

        session = self._mock_session_with_users(mock_users)

        with (
            patch("src.routers.cron.GmailOAuthService") as mock_oauth_class,
            patch("src.routers.cron.GmailWatchService") as mock_watch_class,
        ):
            mock_oauth = MagicMock()
            mock_oauth.ensure_valid_access_token = AsyncMock(
                side_effect=[
                    None,  # First user: token refresh fails
                    {
                        "access_token": "access-2",
                        "expires_at": datetime.now(timezone.utc),
                    },  # Second user: succeeds
                ]
            )
            mock_oauth_class.return_value = mock_oauth

            mock_watch = MagicMock()
            mock_watch.setup_watch = AsyncMock(
                return_value=GmailWatchResult(
                    success=True,
                    history_id="h-123",
                    expiration=datetime.now(timezone.utc),
                )
            )
            mock_watch_class.return_value = mock_watch

            response = await renew_gmail_watches(session=session)

        assert response.total == 2
        assert response.succeeded == 1
        assert response.failed == 1

    @pytest.mark.asyncio
    async def test_zero_users_returns_empty(self):
        """When no Gmail-connected users exist, returns total: 0."""
        from src.routers.cron import renew_gmail_watches

        session = self._mock_session_with_users([])

        response = await renew_gmail_watches(session=session)

        assert response.total == 0
        assert response.succeeded == 0
        assert response.failed == 0
        assert response.details == []
