"""Tests for /api/contacts endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.auth.schemas import FirebaseUser
from src.database import get_db


class TestContactsEndpoint:
    """Tests for contacts API endpoints."""

    @pytest.fixture
    def mock_user(self) -> FirebaseUser:
        """Create a mock authenticated user."""
        return FirebaseUser(uid="test-uid-123", email="test@example.com")

    @pytest.fixture
    def mock_session(self) -> MagicMock:
        """Create a mock database session."""
        session = MagicMock()
        session.commit = AsyncMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def mock_user_model(self) -> MagicMock:
        """Create a mock User model."""
        user = MagicMock()
        user.id = UUID("019494a5-eb1c-7000-8000-000000000001")
        user.firebase_uid = "test-uid-123"
        user.email = "test@example.com"
        user.gmail_access_token = "test-access-token"
        return user

    @pytest.fixture
    def mock_contact_model(self) -> MagicMock:
        """Create a mock Contact model."""
        from datetime import datetime, timezone

        contact = MagicMock()
        contact.id = UUID("019494a5-eb1c-7000-8000-000000000002")
        contact.user_id = UUID("019494a5-eb1c-7000-8000-000000000001")
        contact.contact_email = "boss@example.com"
        contact.contact_name = "上司太郎"
        contact.gmail_query = "from:boss@example.com"
        contact.is_learning_complete = False
        contact.learning_failed_at = None
        contact.created_at = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        return contact

    # ----------------------------
    # POST /api/contacts Tests
    # ----------------------------

    @pytest.mark.asyncio
    async def test_create_contact_without_auth_returns_401(
        self, mock_session: MagicMock
    ) -> None:
        """Request without authentication should return 401."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/contacts",
                json={"contactEmail": "boss@example.com"},
            )

        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "missing_token"

    @pytest.mark.asyncio
    async def test_create_contact_returns_201_with_learning_started(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
        mock_contact_model: MagicMock,
    ) -> None:
        """Creating a contact should return 201 with status learning_started."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.create_contact",
                new=AsyncMock(return_value=mock_contact_model),
            ),
            patch("src.routers.contacts.LearningService"),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/contacts",
                    json={
                        "contactEmail": "boss@example.com",
                        "contactName": "上司太郎",
                        "gmailQuery": "from:boss@example.com",
                    },
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 201
        data = response.json()
        assert data["contactEmail"] == "boss@example.com"
        assert data["contactName"] == "上司太郎"
        assert data["status"] == "learning_started"
        assert data["isLearningComplete"] is False

    @pytest.mark.asyncio
    async def test_create_contact_triggers_background_learning(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
        mock_contact_model: MagicMock,
    ) -> None:
        """Creating a contact should trigger background learning task."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        mock_bg_tasks = MagicMock()

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.create_contact",
                new=AsyncMock(return_value=mock_contact_model),
            ),
            patch("src.routers.contacts.BackgroundTasks", return_value=mock_bg_tasks),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                await client.post(
                    "/api/contacts",
                    json={"contactEmail": "boss@example.com"},
                    headers={"Authorization": "Bearer valid_token"},
                )

    @pytest.mark.asyncio
    async def test_create_contact_with_duplicate_returns_409(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Creating a duplicate contact should return 409 Conflict."""
        from src.repositories.contact_repository import DuplicateContactError
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.create_contact",
                new=AsyncMock(
                    side_effect=DuplicateContactError("Contact already exists")
                ),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/contacts",
                    json={"contactEmail": "boss@example.com"},
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 409
        assert response.json()["detail"]["error"] == "duplicate_contact"

    @pytest.mark.asyncio
    async def test_create_contact_with_invalid_email_returns_400(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
    ) -> None:
        """Creating a contact with invalid email format should return 400."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        with patch("src.auth.middleware.auth") as mock_auth:
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/contacts",
                    json={"contactEmail": "invalid-email"},
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 422  # Pydantic validation error

    # ----------------------------
    # GET /api/contacts Tests
    # ----------------------------

    @pytest.mark.asyncio
    async def test_get_contacts_without_auth_returns_401(
        self, mock_session: MagicMock
    ) -> None:
        """Request without authentication should return 401."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/contacts")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_contacts_returns_user_contacts(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
        mock_contact_model: MagicMock,
    ) -> None:
        """Authenticated user should receive their contacts."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contacts_by_user_id",
                new=AsyncMock(return_value=[mock_contact_model]),
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
                    "/api/contacts",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert "contacts" in data
        assert "total" in data
        assert data["total"] == 1
        assert len(data["contacts"]) == 1
        assert data["contacts"][0]["contactEmail"] == "boss@example.com"

    @pytest.mark.asyncio
    async def test_get_contacts_returns_empty_list_when_no_contacts(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """User with no contacts should receive empty list."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contacts_by_user_id",
                new=AsyncMock(return_value=[]),
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
                    "/api/contacts",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["contacts"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_get_contacts_includes_learning_status(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Contact response should include learning status fields."""
        from datetime import datetime, timezone

        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        # Create contacts with different learning states
        learning_contact = MagicMock()
        learning_contact.id = UUID("019494a5-eb1c-7000-8000-000000000002")
        learning_contact.user_id = mock_user_model.id
        learning_contact.contact_email = "learning@example.com"
        learning_contact.contact_name = None
        learning_contact.gmail_query = None
        learning_contact.is_learning_complete = False
        learning_contact.learning_failed_at = None
        learning_contact.created_at = datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
        )

        complete_contact = MagicMock()
        complete_contact.id = UUID("019494a5-eb1c-7000-8000-000000000003")
        complete_contact.user_id = mock_user_model.id
        complete_contact.contact_email = "complete@example.com"
        complete_contact.contact_name = "完了さん"
        complete_contact.gmail_query = None
        complete_contact.is_learning_complete = True
        complete_contact.learning_failed_at = None
        complete_contact.created_at = datetime(
            2024, 1, 14, 9, 0, 0, tzinfo=timezone.utc
        )

        failed_contact = MagicMock()
        failed_contact.id = UUID("019494a5-eb1c-7000-8000-000000000004")
        failed_contact.user_id = mock_user_model.id
        failed_contact.contact_email = "failed@example.com"
        failed_contact.contact_name = None
        failed_contact.gmail_query = None
        failed_contact.is_learning_complete = False
        failed_contact.learning_failed_at = datetime(
            2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc
        )
        failed_contact.created_at = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contacts_by_user_id",
                new=AsyncMock(
                    return_value=[learning_contact, complete_contact, failed_contact]
                ),
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
                    "/api/contacts",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()

        # Check learning_started status
        learning = next(
            c for c in data["contacts"] if c["contactEmail"] == "learning@example.com"
        )
        assert learning["status"] == "learning_started"
        assert learning["isLearningComplete"] is False

        # Check learning_complete status
        complete = next(
            c for c in data["contacts"] if c["contactEmail"] == "complete@example.com"
        )
        assert complete["status"] == "learning_complete"
        assert complete["isLearningComplete"] is True

        # Check learning_failed status
        failed = next(
            c for c in data["contacts"] if c["contactEmail"] == "failed@example.com"
        )
        assert failed["status"] == "learning_failed"
        assert failed["isLearningComplete"] is False
        assert failed["learningFailedAt"] is not None

    # ----------------------------
    # DELETE /api/contacts/{id} Tests
    # ----------------------------

    @pytest.mark.asyncio
    async def test_delete_contact_without_auth_returns_401(
        self, mock_session: MagicMock
    ) -> None:
        """Request without authentication should return 401."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                "/api/contacts/019494a5-eb1c-7000-8000-000000000002"
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_contact_returns_204_on_success(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
        mock_contact_model: MagicMock,
    ) -> None:
        """Deleting own contact should return 204 No Content."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=mock_contact_model),
            ),
            patch(
                "src.routers.contacts.delete_contact",
                new=AsyncMock(return_value=True),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.delete(
                    f"/api/contacts/{mock_contact_model.id}",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_contact_not_found_returns_404(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Deleting non-existent contact should return 404."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=None),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.delete(
                    "/api/contacts/019494a5-eb1c-7000-8000-000000000099",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 404
        assert response.json()["detail"]["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_delete_other_user_contact_returns_403(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Deleting another user's contact should return 403."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        # Create a contact belonging to a different user
        other_user_contact = MagicMock()
        other_user_contact.id = UUID("019494a5-eb1c-7000-8000-000000000099")
        other_user_contact.user_id = UUID(
            "019494a5-eb1c-7000-8000-000000000999"
        )  # Different user

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=other_user_contact),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.delete(
                    f"/api/contacts/{other_user_contact.id}",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "forbidden"

    # ----------------------------
    # POST /api/contacts/{id}/retry Tests
    # ----------------------------

    @pytest.mark.asyncio
    async def test_retry_learning_without_auth_returns_401(
        self, mock_session: MagicMock
    ) -> None:
        """Request without authentication should return 401."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/contacts/019494a5-eb1c-7000-8000-000000000002/retry"
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_retry_learning_returns_200_with_learning_started(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Retrying learning should reset status and return 200 with learning_started."""
        from datetime import datetime, timezone

        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        # Contact with failed learning
        failed_contact = MagicMock()
        failed_contact.id = UUID("019494a5-eb1c-7000-8000-000000000002")
        failed_contact.user_id = UUID("019494a5-eb1c-7000-8000-000000000001")
        failed_contact.contact_email = "boss@example.com"
        failed_contact.contact_name = "上司太郎"
        failed_contact.gmail_query = "from:boss@example.com"
        failed_contact.is_learning_complete = False
        failed_contact.learning_failed_at = datetime(
            2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc
        )
        failed_contact.created_at = datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
        )

        def simulate_refresh(obj):
            """Simulate DB refresh after status reset."""
            obj.is_learning_complete = False
            obj.learning_failed_at = None

        mock_session.refresh = AsyncMock(side_effect=simulate_refresh)

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=failed_contact),
            ),
            patch(
                "src.routers.contacts.update_contact_learning_status",
                new=AsyncMock(),
            ),
            patch(
                "src.routers.contacts.delete_contact_context_by_contact_id",
                new=AsyncMock(),
            ),
            patch("src.routers.contacts.LearningService"),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/contacts/{failed_contact.id}/retry",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["contactEmail"] == "boss@example.com"
        assert data["status"] == "learning_started"
        assert data["isLearningComplete"] is False
        assert data["learningFailedAt"] is None

    @pytest.mark.asyncio
    async def test_retry_learning_not_found_returns_404(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Retrying learning on non-existent contact should return 404."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=None),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/contacts/019494a5-eb1c-7000-8000-000000000099/retry",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 404
        assert response.json()["detail"]["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_retry_learning_other_user_returns_403(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Retrying learning on another user's contact should return 403."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        other_user_contact = MagicMock()
        other_user_contact.id = UUID("019494a5-eb1c-7000-8000-000000000099")
        other_user_contact.user_id = UUID("019494a5-eb1c-7000-8000-000000000999")

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=other_user_contact),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/contacts/{other_user_contact.id}/retry",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "forbidden"

    @pytest.mark.asyncio
    async def test_retry_learning_not_failed_returns_409(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Retrying learning on a non-failed contact should return 409."""
        from datetime import datetime, timezone

        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        # Contact that is currently learning (not failed)
        learning_contact = MagicMock()
        learning_contact.id = UUID("019494a5-eb1c-7000-8000-000000000002")
        learning_contact.user_id = UUID("019494a5-eb1c-7000-8000-000000000001")
        learning_contact.contact_email = "boss@example.com"
        learning_contact.contact_name = "上司太郎"
        learning_contact.gmail_query = None
        learning_contact.is_learning_complete = False
        learning_contact.learning_failed_at = None
        learning_contact.created_at = datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=learning_contact),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/contacts/{learning_contact.id}/retry",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 409
        assert response.json()["detail"]["error"] == "not_failed"

    # ----------------------------
    # POST /api/contacts/{id}/relearn Tests
    # ----------------------------

    @pytest.mark.asyncio
    async def test_relearn_without_auth_returns_401(
        self, mock_session: MagicMock
    ) -> None:
        """Request without authentication should return 401."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/contacts/019494a5-eb1c-7000-8000-000000000002/relearn"
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_relearn_completed_contact_returns_202_with_learning_started(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Relearning a completed contact should return 202 with learning_started."""
        from datetime import datetime, timezone

        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        # Contact with completed learning
        completed_contact = MagicMock()
        completed_contact.id = UUID("019494a5-eb1c-7000-8000-000000000002")
        completed_contact.user_id = UUID("019494a5-eb1c-7000-8000-000000000001")
        completed_contact.contact_email = "boss@example.com"
        completed_contact.contact_name = "上司太郎"
        completed_contact.gmail_query = "from:boss@example.com"
        completed_contact.is_learning_complete = True
        completed_contact.learning_failed_at = None
        completed_contact.created_at = datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
        )

        def simulate_refresh(obj):
            """Simulate DB refresh after status reset."""
            obj.is_learning_complete = False
            obj.learning_failed_at = None

        mock_session.refresh = AsyncMock(side_effect=simulate_refresh)

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=completed_contact),
            ),
            patch(
                "src.routers.contacts.update_contact_learning_status",
                new=AsyncMock(),
            ),
            patch(
                "src.routers.contacts.delete_contact_context_by_contact_id",
                new=AsyncMock(),
            ),
            patch("src.routers.contacts.LearningService"),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/contacts/{completed_contact.id}/relearn",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 202
        data = response.json()
        assert data["contactEmail"] == "boss@example.com"
        assert data["status"] == "learning_started"
        assert data["isLearningComplete"] is False
        assert data["learningFailedAt"] is None

    @pytest.mark.asyncio
    async def test_relearn_not_found_returns_404(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Relearning a non-existent contact should return 404."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=None),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/contacts/019494a5-eb1c-7000-8000-000000000099/relearn",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 404
        assert response.json()["detail"]["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_relearn_other_user_returns_403(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Relearning another user's contact should return 403."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        other_user_contact = MagicMock()
        other_user_contact.id = UUID("019494a5-eb1c-7000-8000-000000000099")
        other_user_contact.user_id = UUID("019494a5-eb1c-7000-8000-000000000999")

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=other_user_contact),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/contacts/{other_user_contact.id}/relearn",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "forbidden"

    @pytest.mark.asyncio
    async def test_relearn_learning_started_contact_returns_409(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Relearning a contact that is currently learning should return 409."""
        from datetime import datetime, timezone

        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        # Contact currently learning (not complete)
        learning_contact = MagicMock()
        learning_contact.id = UUID("019494a5-eb1c-7000-8000-000000000002")
        learning_contact.user_id = UUID("019494a5-eb1c-7000-8000-000000000001")
        learning_contact.is_learning_complete = False
        learning_contact.learning_failed_at = None
        learning_contact.created_at = datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=learning_contact),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/contacts/{learning_contact.id}/relearn",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 409
        assert response.json()["detail"]["error"] == "not_completed"

    # ----------------------------
    # POST /api/contacts/{id}/instruct Tests
    # ----------------------------

    @pytest.mark.asyncio
    async def test_instruct_without_auth_returns_401(
        self, mock_session: MagicMock
    ) -> None:
        """Request without authentication should return 401."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/contacts/019494a5-eb1c-7000-8000-000000000002/instruct",
                json={"instruction": "テスト指示"},
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_instruct_completed_contact_returns_202(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Instructing a completed contact should return 202 Accepted."""
        from datetime import datetime, timezone

        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        completed_contact = MagicMock()
        completed_contact.id = UUID("019494a5-eb1c-7000-8000-000000000002")
        completed_contact.user_id = UUID("019494a5-eb1c-7000-8000-000000000001")
        completed_contact.contact_email = "boss@example.com"
        completed_contact.contact_name = "上司太郎"
        completed_contact.gmail_query = "from:boss@example.com"
        completed_contact.is_learning_complete = True
        completed_contact.learning_failed_at = None
        completed_contact.created_at = datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
        )

        mock_context = MagicMock()
        mock_context.learned_patterns = '{"contactCharacteristics": {}, "userReplyPatterns": {}}'

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=completed_contact),
            ),
            patch(
                "src.routers.contacts.get_contact_context_by_contact_id",
                new=AsyncMock(return_value=mock_context),
            ),
            patch(
                "src.routers.contacts.update_contact_learning_status",
                new=AsyncMock(),
            ),
            patch("src.routers.contacts.InstructionService"),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/contacts/{completed_contact.id}/instruct",
                    json={"instruction": "文章の最後には'田中より'と追加して"},
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 202
        data = response.json()
        assert data["contactEmail"] == "boss@example.com"

    @pytest.mark.asyncio
    async def test_instruct_not_found_returns_404(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Instructing a non-existent contact should return 404."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=None),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    "/api/contacts/019494a5-eb1c-7000-8000-000000000099/instruct",
                    json={"instruction": "テスト指示"},
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 404
        assert response.json()["detail"]["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_instruct_other_user_returns_403(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Instructing another user's contact should return 403."""
        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        other_user_contact = MagicMock()
        other_user_contact.id = UUID("019494a5-eb1c-7000-8000-000000000099")
        other_user_contact.user_id = UUID("019494a5-eb1c-7000-8000-000000000999")

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=other_user_contact),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/contacts/{other_user_contact.id}/instruct",
                    json={"instruction": "テスト指示"},
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 403
        assert response.json()["detail"]["error"] == "forbidden"

    @pytest.mark.asyncio
    async def test_instruct_not_completed_returns_409(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Instructing a contact that is not learning_complete should return 409."""
        from datetime import datetime, timezone

        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        learning_contact = MagicMock()
        learning_contact.id = UUID("019494a5-eb1c-7000-8000-000000000002")
        learning_contact.user_id = UUID("019494a5-eb1c-7000-8000-000000000001")
        learning_contact.is_learning_complete = False
        learning_contact.learning_failed_at = None
        learning_contact.created_at = datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=learning_contact),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/contacts/{learning_contact.id}/instruct",
                    json={"instruction": "テスト指示"},
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 409
        assert response.json()["detail"]["error"] == "not_completed"

    @pytest.mark.asyncio
    async def test_instruct_no_context_returns_409(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Instructing a contact without context should return 409."""
        from datetime import datetime, timezone

        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        completed_contact = MagicMock()
        completed_contact.id = UUID("019494a5-eb1c-7000-8000-000000000002")
        completed_contact.user_id = UUID("019494a5-eb1c-7000-8000-000000000001")
        completed_contact.is_learning_complete = True
        completed_contact.learning_failed_at = None
        completed_contact.created_at = datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=completed_contact),
            ),
            patch(
                "src.routers.contacts.get_contact_context_by_contact_id",
                new=AsyncMock(return_value=None),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/contacts/{completed_contact.id}/instruct",
                    json={"instruction": "テスト指示"},
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 409
        assert response.json()["detail"]["error"] == "no_context"

    @pytest.mark.asyncio
    async def test_relearn_failed_contact_returns_409(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
        mock_user_model: MagicMock,
    ) -> None:
        """Relearning a failed contact should return 409 (use retry instead)."""
        from datetime import datetime, timezone

        from src.routers.contacts import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        # Contact with failed learning
        failed_contact = MagicMock()
        failed_contact.id = UUID("019494a5-eb1c-7000-8000-000000000002")
        failed_contact.user_id = UUID("019494a5-eb1c-7000-8000-000000000001")
        failed_contact.is_learning_complete = False
        failed_contact.learning_failed_at = datetime(
            2024, 1, 15, 11, 0, 0, tzinfo=timezone.utc
        )
        failed_contact.created_at = datetime(
            2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.contacts.get_user_by_firebase_uid",
                new=AsyncMock(return_value=mock_user_model),
            ),
            patch(
                "src.routers.contacts.get_contact_by_id",
                new=AsyncMock(return_value=failed_contact),
            ),
        ):
            mock_auth.verify_id_token.return_value = {
                "uid": mock_user.uid,
                "email": mock_user.email,
            }

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                response = await client.post(
                    f"/api/contacts/{failed_contact.id}/relearn",
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 409
        assert response.json()["detail"]["error"] == "not_completed"
