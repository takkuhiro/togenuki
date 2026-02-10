"""Tests for Characters API endpoints.

Tests for:
- GET /api/characters - List all available characters (public, no auth)
- GET /api/users/character - Get current user's selected character (auth required)
- PUT /api/users/character - Update user's selected character (auth required)

Requirements Coverage: 2.1, 2.2, 3.1
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.models import User


class TestGetCharacters:
    """Tests for GET /api/characters endpoint.

    Requirements:
    - 2.1: Return all characters with ID, display name, description
    - 2.2: Accessible without authentication (public)
    """

    @pytest.mark.asyncio
    async def test_get_characters_returns_all_characters(self) -> None:
        """Requirement 2.1: Returns all predefined characters."""
        from src.routers.characters import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/characters")

        assert response.status_code == 200
        data = response.json()
        assert "characters" in data
        assert len(data["characters"]) == 3

        # Verify each character has required fields
        for char in data["characters"]:
            assert "id" in char
            assert "displayName" in char
            assert "description" in char

    @pytest.mark.asyncio
    async def test_get_characters_contains_gyaru(self) -> None:
        """Requirement 2.1: Characters include gyaru."""
        from src.routers.characters import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/characters")

        data = response.json()
        ids = [c["id"] for c in data["characters"]]
        assert "gyaru" in ids
        assert "senpai" in ids
        assert "butler" in ids

    @pytest.mark.asyncio
    async def test_get_characters_no_auth_required(self) -> None:
        """Requirement 2.2: Characters endpoint is accessible without auth."""
        from src.routers.characters import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            # No Authorization header
            response = await client.get("/api/characters")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_characters_does_not_expose_system_prompt(self) -> None:
        """Characters response should not include system prompts or voice names."""
        from src.routers.characters import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/characters")

        data = response.json()
        for char in data["characters"]:
            assert "systemPrompt" not in char
            assert "system_prompt" not in char
            assert "ttsVoiceName" not in char
            assert "tts_voice_name" not in char


class TestGetUserCharacter:
    """Tests for GET /api/users/character endpoint.

    Requirement: 3.1 (partial - get current selection)
    """

    @pytest.fixture
    def mock_user(self) -> User:
        """Create a mock user."""
        from uuid6 import uuid7

        return User(
            id=uuid7(),
            firebase_uid="test-uid-char",
            email="char-test@example.com",
            selected_character_id="senpai",
        )

    @pytest.mark.asyncio
    async def test_get_user_character_returns_selected(self, mock_user: User) -> None:
        """Returns the user's currently selected character."""
        from src.routers.characters import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.characters.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.firebase_uid,
                "email": mock_user.email,
            }

            mock_session = MagicMock()
            from src.database import get_db

            test_app.dependency_overrides[get_db] = lambda: mock_session

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/users/character",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "senpai"
        assert data["displayName"] == "優しい先輩"

    @pytest.mark.asyncio
    async def test_get_user_character_default_when_null(self) -> None:
        """Returns default character (gyaru) when user has no selection."""
        from uuid6 import uuid7

        from src.routers.characters import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        user_no_char = User(
            id=uuid7(),
            firebase_uid="test-uid-nochar",
            email="nochar@example.com",
            selected_character_id=None,
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.characters.get_user_by_firebase_uid",
                new=AsyncMock(return_value=user_no_char),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": user_no_char.firebase_uid,
                "email": user_no_char.email,
            }

            mock_session = MagicMock()
            from src.database import get_db

            test_app.dependency_overrides[get_db] = lambda: mock_session

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.get(
                    "/api/users/character",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "gyaru"

    @pytest.mark.asyncio
    async def test_get_user_character_requires_auth(self) -> None:
        """Returns 401 when no auth token provided."""
        from src.routers.characters import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.get("/api/users/character")

        assert response.status_code == 401


class TestUpdateUserCharacter:
    """Tests for PUT /api/users/character endpoint.

    Requirement: 3.1 (update character selection)
    """

    @pytest.fixture
    def mock_user(self) -> User:
        """Create a mock user."""
        from uuid6 import uuid7

        return User(
            id=uuid7(),
            firebase_uid="test-uid-update",
            email="update@example.com",
            selected_character_id="gyaru",
        )

    @pytest.mark.asyncio
    async def test_update_character_success(self, mock_user: User) -> None:
        """Successfully updates user's character selection."""
        from src.routers.characters import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        mock_session = MagicMock()
        mock_session.commit = AsyncMock()

        from src.database import get_db

        test_app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.characters.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.firebase_uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/users/character",
                    json={"characterId": "butler"},
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "butler"
        assert data["displayName"] == "冷静な執事"
        # User model should be updated
        assert mock_user.selected_character_id == "butler"
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_character_invalid_id_returns_400(
        self, mock_user: User
    ) -> None:
        """Returns 400 for invalid character ID."""
        from src.routers.characters import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        mock_session = MagicMock()
        from src.database import get_db

        test_app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.characters.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.firebase_uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=test_app), base_url="http://test"
            ) as client:
                response = await client.put(
                    "/api/users/character",
                    json={"characterId": "nonexistent"},
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 400
        data = response.json()
        assert data["detail"]["error"] == "invalid_character_id"

    @pytest.mark.asyncio
    async def test_update_character_requires_auth(self) -> None:
        """Returns 401 when no auth token provided."""
        from src.routers.characters import router

        test_app = FastAPI()
        test_app.include_router(router, prefix="/api")

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as client:
            response = await client.put(
                "/api/users/character",
                json={"characterId": "butler"},
            )

        assert response.status_code == 401
