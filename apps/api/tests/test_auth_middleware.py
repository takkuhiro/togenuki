"""Tests for Firebase Authentication middleware."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient


class TestAuthMiddleware:
    """Firebase Authentication middleware tests."""

    @pytest.fixture
    def mock_firebase_admin(self) -> MagicMock:
        """Mock firebase_admin module."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_missing_authorization_header_returns_401(self) -> None:
        """Request without Authorization header should return 401."""
        from src.auth.middleware import get_current_user
        from src.auth.schemas import FirebaseUser

        app = FastAPI()

        @app.get("/protected")
        async def protected_route(
            user: FirebaseUser = Depends(get_current_user),
        ) -> dict:
            return {"uid": user.uid}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/protected")

        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "missing_token"

    @pytest.mark.asyncio
    async def test_invalid_bearer_format_returns_401(self) -> None:
        """Request with invalid Bearer format should return 401."""
        from src.auth.middleware import get_current_user
        from src.auth.schemas import FirebaseUser

        app = FastAPI()

        @app.get("/protected")
        async def protected_route(
            user: FirebaseUser = Depends(get_current_user),
        ) -> dict:
            return {"uid": user.uid}

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/protected",
                headers={"Authorization": "InvalidFormat token123"},
            )

        # HTTPBearer with auto_error=False returns None for non-Bearer schemes
        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "missing_token"

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self) -> None:
        """Request with expired token should return 401."""
        from src.auth.middleware import get_current_user
        from src.auth.schemas import FirebaseUser

        app = FastAPI()

        @app.get("/protected")
        async def protected_route(
            user: FirebaseUser = Depends(get_current_user),
        ) -> dict:
            return {"uid": user.uid}

        with patch("src.auth.middleware.auth") as mock_auth:
            mock_auth.verify_id_token.side_effect = Exception("Token expired")

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/protected",
                    headers={"Authorization": "Bearer expired_token"},
                )

        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "expired_token"

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self) -> None:
        """Request with valid token should return user information."""
        from src.auth.middleware import get_current_user
        from src.auth.schemas import FirebaseUser

        app = FastAPI()

        @app.get("/protected")
        async def protected_route(
            user: FirebaseUser = Depends(get_current_user),
        ) -> dict:
            return {"uid": user.uid, "email": user.email}

        with patch("src.auth.middleware.auth") as mock_auth:
            mock_auth.verify_id_token.return_value = {
                "uid": "test-uid-123",
                "email": "test@example.com",
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/protected",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        assert response.json() == {"uid": "test-uid-123", "email": "test@example.com"}

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self) -> None:
        """Request with invalid token should return 401."""
        from src.auth.middleware import get_current_user
        from src.auth.schemas import FirebaseUser

        app = FastAPI()

        @app.get("/protected")
        async def protected_route(
            user: FirebaseUser = Depends(get_current_user),
        ) -> dict:
            return {"uid": user.uid}

        with patch("src.auth.middleware.auth") as mock_auth:
            mock_auth.verify_id_token.side_effect = Exception("Invalid token")

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/protected",
                    headers={"Authorization": "Bearer invalid_token"},
                )

        assert response.status_code == 401


class TestAuthError:
    """AuthError enum tests."""

    def test_auth_error_values(self) -> None:
        """AuthError should have expected error types."""
        from src.auth.schemas import AuthError

        assert AuthError.INVALID_TOKEN.value == "invalid_token"
        assert AuthError.EXPIRED_TOKEN.value == "expired_token"
        assert AuthError.MISSING_TOKEN.value == "missing_token"


class TestFirebaseUser:
    """FirebaseUser schema tests."""

    def test_firebase_user_fields(self) -> None:
        """FirebaseUser should have uid and email fields."""
        from src.auth.schemas import FirebaseUser

        user = FirebaseUser(uid="test-uid", email="test@example.com")

        assert user.uid == "test-uid"
        assert user.email == "test@example.com"
