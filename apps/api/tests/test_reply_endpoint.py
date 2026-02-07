"""Tests for reply API endpoints (compose-reply and send-reply)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.auth.schemas import FirebaseUser
from src.database import get_db


class TestComposeReplyEndpoint:
    """Tests for POST /api/emails/{email_id}/compose-reply endpoint."""

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

    @pytest.mark.asyncio
    async def test_compose_reply_without_auth_returns_401(
        self, mock_session: MagicMock
    ) -> None:
        """Request without authentication should return 401."""
        from src.routers.reply import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/emails/019494a5-eb1c-7000-8000-000000000001/compose-reply",
                json={"rawText": "了解っす"},
            )

        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "missing_token"

    @pytest.mark.asyncio
    async def test_compose_reply_success_returns_200(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
    ) -> None:
        """Successful compose-reply should return 200 with composed text."""
        from result import Ok

        from src.routers.reply import router
        from src.services.reply_service import ComposeReplyResult

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        mock_reply_service = MagicMock()
        mock_reply_service.compose_reply = AsyncMock(
            return_value=Ok(
                ComposeReplyResult(
                    composed_body="お疲れ様です。承知いたしました。",
                    composed_subject="Re: 報告書について",
                )
            )
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.reply.ReplyService",
                return_value=mock_reply_service,
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
                    "/api/emails/019494a5-eb1c-7000-8000-000000000001/compose-reply",
                    json={"rawText": "了解っす、明日出します"},
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["composedBody"] == "お疲れ様です。承知いたしました。"
        assert data["composedSubject"] == "Re: 報告書について"

    @pytest.mark.asyncio
    async def test_compose_reply_empty_text_returns_422(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
    ) -> None:
        """Empty rawText should return 422 validation error."""
        from src.routers.reply import router

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
                    "/api/emails/019494a5-eb1c-7000-8000-000000000001/compose-reply",
                    json={"rawText": ""},
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_compose_reply_email_not_found_returns_404(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
    ) -> None:
        """compose-reply with non-existent email should return 404."""
        from result import Err

        from src.routers.reply import router
        from src.services.reply_service import ReplyError

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        mock_reply_service = MagicMock()
        mock_reply_service.compose_reply = AsyncMock(
            return_value=Err(ReplyError.EMAIL_NOT_FOUND)
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.reply.ReplyService",
                return_value=mock_reply_service,
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
                    "/api/emails/019494a5-eb1c-7000-8000-000000000099/compose-reply",
                    json={"rawText": "了解です"},
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 404
        assert response.json()["detail"]["error"] == "email_not_found"

    @pytest.mark.asyncio
    async def test_compose_reply_compose_failed_returns_503(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
    ) -> None:
        """compose-reply with Gemini failure should return 503."""
        from result import Err

        from src.routers.reply import router
        from src.services.reply_service import ReplyError

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        mock_reply_service = MagicMock()
        mock_reply_service.compose_reply = AsyncMock(
            return_value=Err(ReplyError.COMPOSE_FAILED)
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.reply.ReplyService",
                return_value=mock_reply_service,
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
                    "/api/emails/019494a5-eb1c-7000-8000-000000000001/compose-reply",
                    json={"rawText": "了解です"},
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 503
        assert response.json()["detail"]["error"] == "compose_failed"


class TestSendReplyEndpoint:
    """Tests for POST /api/emails/{email_id}/send-reply endpoint."""

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

    @pytest.mark.asyncio
    async def test_send_reply_without_auth_returns_401(
        self, mock_session: MagicMock
    ) -> None:
        """Request without authentication should return 401."""
        from src.routers.reply import router

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/emails/019494a5-eb1c-7000-8000-000000000001/send-reply",
                json={
                    "composedBody": "お疲れ様です。",
                    "composedSubject": "Re: テスト",
                },
            )

        assert response.status_code == 401
        assert response.json()["detail"]["error"] == "missing_token"

    @pytest.mark.asyncio
    async def test_send_reply_success_returns_200(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
    ) -> None:
        """Successful send-reply should return 200 with success and messageId."""
        from result import Ok

        from src.routers.reply import router
        from src.services.reply_service import SendReplyResult

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        mock_reply_service = MagicMock()
        mock_reply_service.send_reply = AsyncMock(
            return_value=Ok(SendReplyResult(google_message_id="sent-msg-456"))
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.reply.ReplyService",
                return_value=mock_reply_service,
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
                    "/api/emails/019494a5-eb1c-7000-8000-000000000001/send-reply",
                    json={
                        "composedBody": "お疲れ様です。承知いたしました。",
                        "composedSubject": "Re: 報告書について",
                    },
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["googleMessageId"] == "sent-msg-456"

    @pytest.mark.asyncio
    async def test_send_reply_already_replied_returns_409(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
    ) -> None:
        """send-reply on already replied email should return 409."""
        from result import Err

        from src.routers.reply import router
        from src.services.reply_service import ReplyError

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        mock_reply_service = MagicMock()
        mock_reply_service.send_reply = AsyncMock(
            return_value=Err(ReplyError.ALREADY_REPLIED)
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.reply.ReplyService",
                return_value=mock_reply_service,
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
                    "/api/emails/019494a5-eb1c-7000-8000-000000000001/send-reply",
                    json={
                        "composedBody": "本文",
                        "composedSubject": "Re: テスト",
                    },
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 409
        assert response.json()["detail"]["error"] == "already_replied"

    @pytest.mark.asyncio
    async def test_send_reply_email_not_found_returns_404(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
    ) -> None:
        """send-reply with non-existent email should return 404."""
        from result import Err

        from src.routers.reply import router
        from src.services.reply_service import ReplyError

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        mock_reply_service = MagicMock()
        mock_reply_service.send_reply = AsyncMock(
            return_value=Err(ReplyError.EMAIL_NOT_FOUND)
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.reply.ReplyService",
                return_value=mock_reply_service,
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
                    "/api/emails/019494a5-eb1c-7000-8000-000000000099/send-reply",
                    json={
                        "composedBody": "本文",
                        "composedSubject": "Re: テスト",
                    },
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 404
        assert response.json()["detail"]["error"] == "email_not_found"

    @pytest.mark.asyncio
    async def test_send_reply_send_failed_returns_503(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
    ) -> None:
        """send-reply with Gmail API failure should return 503."""
        from result import Err

        from src.routers.reply import router
        from src.services.reply_service import ReplyError

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        mock_reply_service = MagicMock()
        mock_reply_service.send_reply = AsyncMock(
            return_value=Err(ReplyError.SEND_FAILED)
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.reply.ReplyService",
                return_value=mock_reply_service,
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
                    "/api/emails/019494a5-eb1c-7000-8000-000000000001/send-reply",
                    json={
                        "composedBody": "本文",
                        "composedSubject": "Re: テスト",
                    },
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 503
        assert response.json()["detail"]["error"] == "send_failed"

    @pytest.mark.asyncio
    async def test_send_reply_token_expired_returns_503(
        self,
        mock_user: FirebaseUser,
        mock_session: MagicMock,
    ) -> None:
        """send-reply with expired token should return 503."""
        from result import Err

        from src.routers.reply import router
        from src.services.reply_service import ReplyError

        app = FastAPI()
        app.include_router(router, prefix="/api")
        app.dependency_overrides[get_db] = lambda: mock_session

        mock_reply_service = MagicMock()
        mock_reply_service.send_reply = AsyncMock(
            return_value=Err(ReplyError.TOKEN_EXPIRED)
        )

        with (
            patch("src.auth.middleware.auth") as mock_auth,
            patch(
                "src.routers.reply.ReplyService",
                return_value=mock_reply_service,
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
                    "/api/emails/019494a5-eb1c-7000-8000-000000000001/send-reply",
                    json={
                        "composedBody": "本文",
                        "composedSubject": "Re: テスト",
                    },
                    headers={"Authorization": "Bearer valid_token"},
                )

        assert response.status_code == 503
        assert response.json()["detail"]["error"] == "token_expired"
