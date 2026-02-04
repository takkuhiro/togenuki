"""Tests for Gmail OAuth API endpoints."""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.auth.schemas import FirebaseUser


class TestGetGmailAuthUrl:
    """GET /api/auth/gmail/url endpoint tests."""

    @pytest.mark.asyncio
    async def test_get_gmail_auth_url_returns_200(self) -> None:
        """GET /api/auth/gmail/url should return 200 OK."""
        from src.routers.gmail_oauth import router, get_current_user

        app = FastAPI()
        app.include_router(router, prefix="/api/auth/gmail")

        # Override the dependency
        app.dependency_overrides[get_current_user] = lambda: FirebaseUser(
            uid="test-uid", email="test@example.com"
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/auth/gmail/url")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_gmail_auth_url_returns_valid_url(self) -> None:
        """GET /api/auth/gmail/url should return a valid OAuth URL."""
        from src.routers.gmail_oauth import router, get_current_user

        app = FastAPI()
        app.include_router(router, prefix="/api/auth/gmail")

        app.dependency_overrides[get_current_user] = lambda: FirebaseUser(
            uid="test-uid", email="test@example.com"
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/auth/gmail/url")

        data = response.json()
        assert "url" in data
        assert "https://accounts.google.com" in data["url"]

    @pytest.mark.asyncio
    async def test_get_gmail_auth_url_requires_auth(self) -> None:
        """GET /api/auth/gmail/url should require authentication."""
        from src.routers.gmail_oauth import router

        app = FastAPI()
        app.include_router(router, prefix="/api/auth/gmail")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/auth/gmail/url")

        assert response.status_code == 401


class TestPostGmailCallback:
    """POST /api/auth/gmail/callback endpoint tests."""

    @pytest.mark.asyncio
    async def test_post_gmail_callback_returns_200_on_success(self) -> None:
        """POST /api/auth/gmail/callback should return 200 on success."""
        from src.routers.gmail_oauth import router, get_current_user
        from src.database import get_db

        app = FastAPI()
        app.include_router(router, prefix="/api/auth/gmail")

        # Mock user not found (will create new user)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        async def mock_db():
            yield mock_session

        app.dependency_overrides[get_current_user] = lambda: FirebaseUser(
            uid="test-uid", email="test@example.com"
        )
        app.dependency_overrides[get_db] = mock_db

        with patch("src.routers.gmail_oauth.GmailOAuthService") as mock_service:
            mock_service_instance = MagicMock()
            mock_service_instance.exchange_code_for_tokens = AsyncMock(
                return_value={
                    "access_token": "test-access",
                    "refresh_token": "test-refresh",
                    "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
                }
            )
            mock_service.return_value = mock_service_instance

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/auth/gmail/callback",
                    json={"code": "test-code"},
                )

        assert response.status_code == 200
        assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_post_gmail_callback_returns_400_on_invalid_code(self) -> None:
        """POST /api/auth/gmail/callback should return 400 on invalid code."""
        from src.routers.gmail_oauth import router, get_current_user
        from src.database import get_db

        app = FastAPI()
        app.include_router(router, prefix="/api/auth/gmail")

        mock_session = AsyncMock()

        async def mock_db():
            yield mock_session

        app.dependency_overrides[get_current_user] = lambda: FirebaseUser(
            uid="test-uid", email="test@example.com"
        )
        app.dependency_overrides[get_db] = mock_db

        with patch("src.routers.gmail_oauth.GmailOAuthService") as mock_service:
            mock_service_instance = MagicMock()
            mock_service_instance.exchange_code_for_tokens = AsyncMock(return_value=None)
            mock_service.return_value = mock_service_instance

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/auth/gmail/callback",
                    json={"code": "invalid-code"},
                )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_post_gmail_callback_requires_auth(self) -> None:
        """POST /api/auth/gmail/callback should require authentication."""
        from src.routers.gmail_oauth import router

        app = FastAPI()
        app.include_router(router, prefix="/api/auth/gmail")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/auth/gmail/callback", json={"code": "test-code"}
            )

        assert response.status_code == 401


class TestGetGmailStatus:
    """GET /api/auth/gmail/status endpoint tests."""

    @pytest.mark.asyncio
    async def test_get_gmail_status_returns_200(self) -> None:
        """GET /api/auth/gmail/status should return 200 OK."""
        from src.routers.gmail_oauth import router, get_current_user
        from src.database import get_db

        app = FastAPI()
        app.include_router(router, prefix="/api/auth/gmail")

        mock_user = MagicMock()
        mock_user.gmail_refresh_token = "test-refresh-token"
        mock_user.gmail_access_token = "test-access-token"
        mock_user.gmail_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def mock_db():
            yield mock_session

        app.dependency_overrides[get_current_user] = lambda: FirebaseUser(
            uid="test-uid", email="test@example.com"
        )
        app.dependency_overrides[get_db] = mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/auth/gmail/status")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_gmail_status_returns_connected_true_when_token_exists(
        self,
    ) -> None:
        """GET /api/auth/gmail/status should return connected: true if token exists."""
        from src.routers.gmail_oauth import router, get_current_user
        from src.database import get_db

        app = FastAPI()
        app.include_router(router, prefix="/api/auth/gmail")

        mock_user = MagicMock()
        mock_user.gmail_refresh_token = "test-refresh-token"
        mock_user.gmail_access_token = "test-access-token"
        mock_user.gmail_token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def mock_db():
            yield mock_session

        app.dependency_overrides[get_current_user] = lambda: FirebaseUser(
            uid="test-uid", email="test@example.com"
        )
        app.dependency_overrides[get_db] = mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/auth/gmail/status")

        assert response.json()["connected"] is True

    @pytest.mark.asyncio
    async def test_get_gmail_status_returns_connected_false_when_no_token(self) -> None:
        """GET /api/auth/gmail/status should return connected: false if no token."""
        from src.routers.gmail_oauth import router, get_current_user
        from src.database import get_db

        app = FastAPI()
        app.include_router(router, prefix="/api/auth/gmail")

        mock_user = MagicMock()
        mock_user.gmail_refresh_token = None
        mock_user.gmail_access_token = None
        mock_user.gmail_token_expires_at = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def mock_db():
            yield mock_session

        app.dependency_overrides[get_current_user] = lambda: FirebaseUser(
            uid="test-uid", email="test@example.com"
        )
        app.dependency_overrides[get_db] = mock_db

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/auth/gmail/status")

        assert response.json()["connected"] is False

    @pytest.mark.asyncio
    async def test_get_gmail_status_requires_auth(self) -> None:
        """GET /api/auth/gmail/status should require authentication."""
        from src.routers.gmail_oauth import router

        app = FastAPI()
        app.include_router(router, prefix="/api/auth/gmail")

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/auth/gmail/status")

        assert response.status_code == 401
