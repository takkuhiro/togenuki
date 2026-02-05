"""Tests for Gmail Watch API functionality."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from uuid6 import uuid7

from src.auth.schemas import FirebaseUser
from src.models import User


class TestGmailWatchService:
    """Tests for Gmail Watch service."""

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

    @pytest.mark.asyncio
    async def test_setup_gmail_watch_success(self, mock_user: User):
        """Test successful Gmail watch setup."""
        from src.services.gmail_watch import GmailWatchService

        mock_response = {
            "historyId": "12345",
            "expiration": "1704672000000",  # Unix timestamp in ms
        }

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_http_response = MagicMock()
            mock_http_response.status_code = 200
            mock_http_response.json.return_value = mock_response
            mock_client.post.return_value = mock_http_response

            service = GmailWatchService()
            result = await service.setup_watch("access-token-xxx")

        assert result.success is True
        assert result.history_id == "12345"
        assert result.expiration is not None

    @pytest.mark.asyncio
    async def test_setup_gmail_watch_failure(self):
        """Test Gmail watch setup failure."""
        from src.services.gmail_watch import GmailWatchService

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_http_response = MagicMock()
            mock_http_response.status_code = 401
            mock_http_response.text = "Unauthorized"
            mock_client.post.return_value = mock_http_response

            service = GmailWatchService()
            result = await service.setup_watch("invalid-token")

        assert result.success is False
        assert "401" in result.error or "Unauthorized" in result.error

    @pytest.mark.asyncio
    async def test_stop_gmail_watch_success(self):
        """Test stopping Gmail watch."""
        from src.services.gmail_watch import GmailWatchService

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_http_response = MagicMock()
            mock_http_response.status_code = 204
            mock_client.post.return_value = mock_http_response

            service = GmailWatchService()
            result = await service.stop_watch("access-token-xxx")

        assert result is True


class TestGmailWatchEndpoint:
    """Tests for Gmail Watch API endpoint."""

    @pytest.fixture
    def mock_firebase_user(self) -> FirebaseUser:
        """Create a mock Firebase user."""
        return FirebaseUser(uid="test-uid-123", email="user@example.com")

    @pytest.fixture
    def mock_user(self) -> User:
        """Create a mock user."""
        return User(
            id=uuid7(),
            firebase_uid="test-uid-123",
            email="user@example.com",
            gmail_refresh_token="refresh-token",
            gmail_access_token="access-token",
        )

    @pytest.mark.asyncio
    async def test_setup_watch_endpoint_success(
        self, mock_firebase_user: FirebaseUser, mock_user: User
    ):
        """Test POST /api/gmail/watch endpoint success by directly calling router function."""
        from src.routers.gmail_watch import setup_gmail_watch
        from src.services.gmail_watch import GmailWatchResult

        mock_session = AsyncMock()

        with (
            patch(
                "src.routers.gmail_watch.get_user_from_db",
                new_callable=AsyncMock,
                return_value=mock_user,
            ),
            patch("src.routers.gmail_watch.GmailOAuthService") as mock_oauth_class,
        ):
            mock_oauth = MagicMock()
            # Mock ensure_valid_access_token to return valid token
            mock_oauth.ensure_valid_access_token = AsyncMock(
                return_value={
                    "access_token": "access-token",
                    "expires_at": datetime.now(timezone.utc),
                }
            )
            mock_oauth_class.return_value = mock_oauth

            with patch(
                "src.routers.gmail_watch.GmailWatchService"
            ) as mock_service_class:
                mock_service = MagicMock()
                mock_result = GmailWatchResult(
                    success=True,
                    history_id="12345",
                    expiration=datetime.now(timezone.utc),
                )
                mock_service.setup_watch = AsyncMock(return_value=mock_result)
                mock_service_class.return_value = mock_service

                # Call the router function directly
                response = await setup_gmail_watch(
                    firebase_user=mock_firebase_user, session=mock_session
                )

                assert response.success is True
                assert response.history_id == "12345"
                assert response.expiration is not None

    @pytest.mark.asyncio
    async def test_setup_watch_requires_gmail_connection(
        self, mock_firebase_user: FirebaseUser, mock_user: User
    ):
        """Test that watch setup requires Gmail OAuth connection."""
        from fastapi import HTTPException

        from src.routers.gmail_watch import setup_gmail_watch

        # User without Gmail connection
        mock_user.gmail_refresh_token = None

        mock_session = AsyncMock()

        with patch(
            "src.routers.gmail_watch.get_user_from_db",
            new_callable=AsyncMock,
            return_value=mock_user,
        ):
            # Should raise HTTPException with status 400
            with pytest.raises(HTTPException) as exc_info:
                await setup_gmail_watch(
                    firebase_user=mock_firebase_user, session=mock_session
                )

            assert exc_info.value.status_code == 400
            assert "Gmail not connected" in exc_info.value.detail


class TestGmailWatchResult:
    """Tests for GmailWatchResult dataclass."""

    def test_watch_result_success(self):
        """Test successful watch result."""
        from src.services.gmail_watch import GmailWatchResult

        result = GmailWatchResult(
            success=True, history_id="12345", expiration=datetime.now(timezone.utc)
        )

        assert result.success is True
        assert result.history_id == "12345"

    def test_watch_result_failure(self):
        """Test failed watch result."""
        from src.services.gmail_watch import GmailWatchResult

        result = GmailWatchResult(success=False, error="API Error")

        assert result.success is False
        assert result.error == "API Error"
