"""Tests for GET /api/emails endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.auth.schemas import FirebaseUser
from src.database import get_db


class TestEmailsEndpoint:
    """GET /api/emails endpoint tests."""

    @pytest.fixture
    def mock_user(self) -> FirebaseUser:
        """Create a mock authenticated user."""
        return FirebaseUser(uid="test-uid-123", email="test@example.com")

    @pytest.fixture
    def mock_emails_data(self) -> list[dict]:
        """Create mock email data."""
        return [
            {
                "id": "019494a5-eb1c-7000-8000-000000000001",
                "sender_name": "田中部長",
                "sender_email": "tanaka@example.com",
                "subject": "件名テスト1",
                "converted_body": "変換後テキスト1",
                "audio_url": "https://storage.example.com/audio1.mp3",
                "is_processed": True,
                "received_at": "2024-01-15T10:30:00+00:00",
            },
            {
                "id": "019494a5-eb1c-7000-8000-000000000002",
                "sender_name": "佐藤課長",
                "sender_email": "sato@example.com",
                "subject": "件名テスト2",
                "converted_body": None,
                "audio_url": None,
                "is_processed": False,
                "received_at": "2024-01-14T09:00:00+00:00",
            },
        ]

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock database session."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_get_emails_without_auth_returns_401(
        self, mock_session: MagicMock
    ) -> None:
        """Request without authentication should return 401."""
        from src.routers.emails import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/emails")

        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "missing_token"

    @pytest.mark.asyncio
    async def test_get_emails_returns_user_emails_sorted_by_received_at(
        self,
        mock_user: FirebaseUser,
        mock_emails_data: list[dict],
        mock_session: MagicMock,
    ) -> None:
        """Authenticated user should receive their emails sorted by received_at descending."""
        from src.routers.emails import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch.object(
                # Use a different patching approach
                __import__("src.routers.emails", fromlist=["get_user_emails"]),
                "get_user_emails",
                new=AsyncMock(return_value=mock_emails_data),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/emails",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert "emails" in data
        assert "total" in data
        assert data["total"] == 2
        assert len(data["emails"]) == 2

        # Check first email (should be newer)
        first_email = data["emails"][0]
        assert first_email["senderName"] == "田中部長"
        assert first_email["senderEmail"] == "tanaka@example.com"
        assert first_email["subject"] == "件名テスト1"
        assert first_email["convertedBody"] == "変換後テキスト1"
        assert first_email["audioUrl"] == "https://storage.example.com/audio1.mp3"
        assert first_email["isProcessed"] is True

    @pytest.mark.asyncio
    async def test_get_emails_returns_empty_list_when_no_emails(
        self, mock_user: FirebaseUser, mock_session: MagicMock
    ) -> None:
        """User with no emails should receive empty list."""
        from src.routers.emails import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch("src.routers.emails.get_user_emails", new=AsyncMock(return_value=[])),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/emails",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["emails"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_emails_only_returns_own_emails(
        self, mock_user: FirebaseUser, mock_session: MagicMock
    ) -> None:
        """User should only receive their own emails, not other users' emails."""
        from src.routers.emails import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        mock_get_emails = AsyncMock(return_value=[])

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch("src.routers.emails.get_user_emails", mock_get_emails),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.get(
                    "/api/emails",
                    headers={"Authorization": "Bearer valid_token"},
                )

        # Verify get_user_emails was called with correct user identifier
        mock_get_emails.assert_called_once()
        call_args = mock_get_emails.call_args
        # The function should be called with firebase_uid from the authenticated user
        assert mock_user.uid in str(call_args)

    @pytest.mark.asyncio
    async def test_email_response_includes_required_fields(
        self,
        mock_user: FirebaseUser,
        mock_emails_data: list[dict],
        mock_session: MagicMock,
    ) -> None:
        """Email response should include all required fields per design spec."""
        from src.routers.emails import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.emails.get_user_emails",
                new=AsyncMock(return_value=mock_emails_data[:1]),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/emails",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        email = response.json()["emails"][0]

        # Required fields per design.md EmailDTO
        required_fields = [
            "id",
            "senderName",
            "senderEmail",
            "subject",
            "convertedBody",
            "audioUrl",
            "isProcessed",
            "receivedAt",
        ]
        for field in required_fields:
            assert field in email, f"Missing required field: {field}"
