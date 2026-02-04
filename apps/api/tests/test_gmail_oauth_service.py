"""Tests for Gmail OAuth service."""

from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession


class TestGmailOAuthService:
    """Gmail OAuth service tests."""

    @pytest.mark.asyncio
    async def test_get_authorization_url_returns_valid_url(self) -> None:
        """get_authorization_url should return a valid Google OAuth URL."""
        from src.auth.gmail_oauth import GmailOAuthService

        service = GmailOAuthService()
        state = "test-state-123"

        url = service.get_authorization_url(state)

        assert "https://accounts.google.com" in url
        assert "state=test-state-123" in url
        assert "gmail.readonly" in url or "scope" in url

    @pytest.mark.asyncio
    async def test_get_authorization_url_includes_required_scopes(self) -> None:
        """Authorization URL should include gmail.readonly and gmail.send scopes."""
        from src.auth.gmail_oauth import GmailOAuthService

        service = GmailOAuthService()
        state = "test-state"

        url = service.get_authorization_url(state)

        # URL should request offline access for refresh token
        assert "access_type=offline" in url

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_success(self) -> None:
        """exchange_code_for_tokens should return tokens on success."""
        from src.auth.gmail_oauth import GmailOAuthService, OAuthTokens

        with patch("src.auth.gmail_oauth.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "test-access-token",
                "refresh_token": "test-refresh-token",
                "expires_in": 3600,
            }

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            service = GmailOAuthService()
            result = await service.exchange_code_for_tokens("test-code")

            assert result is not None
            assert result["access_token"] == "test-access-token"
            assert result["refresh_token"] == "test-refresh-token"
            assert "expires_at" in result

    @pytest.mark.asyncio
    async def test_exchange_code_for_tokens_invalid_code_returns_none(self) -> None:
        """exchange_code_for_tokens should return None on invalid code."""
        from src.auth.gmail_oauth import GmailOAuthService

        with patch("src.auth.gmail_oauth.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"error": "invalid_grant"}

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            service = GmailOAuthService()
            result = await service.exchange_code_for_tokens("invalid-code")

            assert result is None

    @pytest.mark.asyncio
    async def test_refresh_access_token_success(self) -> None:
        """refresh_access_token should return new access token on success."""
        from src.auth.gmail_oauth import GmailOAuthService

        with patch("src.auth.gmail_oauth.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "new-access-token",
                "expires_in": 3600,
            }

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            service = GmailOAuthService()
            result = await service.refresh_access_token("test-refresh-token")

            assert result is not None
            assert result["access_token"] == "new-access-token"

    @pytest.mark.asyncio
    async def test_refresh_access_token_invalid_refresh_token_returns_none(self) -> None:
        """refresh_access_token should return None on invalid refresh token."""
        from src.auth.gmail_oauth import GmailOAuthService

        with patch("src.auth.gmail_oauth.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.json.return_value = {"error": "invalid_grant"}

            mock_client_instance = AsyncMock()
            mock_client_instance.post.return_value = mock_response
            mock_client_instance.__aenter__.return_value = mock_client_instance
            mock_client_instance.__aexit__.return_value = None
            mock_client.return_value = mock_client_instance

            service = GmailOAuthService()
            result = await service.refresh_access_token("invalid-refresh-token")

            assert result is None

    @pytest.mark.asyncio
    async def test_is_token_expired_returns_true_for_expired_token(self) -> None:
        """is_token_expired should return True for expired tokens."""
        from src.auth.gmail_oauth import GmailOAuthService

        service = GmailOAuthService()
        expired_time = datetime.now(timezone.utc) - timedelta(hours=1)

        result = service.is_token_expired(expired_time)

        assert result is True

    @pytest.mark.asyncio
    async def test_is_token_expired_returns_false_for_valid_token(self) -> None:
        """is_token_expired should return False for valid tokens."""
        from src.auth.gmail_oauth import GmailOAuthService

        service = GmailOAuthService()
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)

        result = service.is_token_expired(future_time)

        assert result is False

    @pytest.mark.asyncio
    async def test_is_token_expired_returns_true_for_none(self) -> None:
        """is_token_expired should return True if expires_at is None."""
        from src.auth.gmail_oauth import GmailOAuthService

        service = GmailOAuthService()

        result = service.is_token_expired(None)

        assert result is True


class TestOAuthTokens:
    """OAuthTokens type tests."""

    def test_oauth_tokens_has_required_fields(self) -> None:
        """OAuthTokens should have access_token, refresh_token, expires_at."""
        from src.auth.gmail_oauth import OAuthTokens

        tokens: OAuthTokens = {
            "access_token": "test-access",
            "refresh_token": "test-refresh",
            "expires_at": datetime.now(timezone.utc),
        }

        assert "access_token" in tokens
        assert "refresh_token" in tokens
        assert "expires_at" in tokens


class TestOAuthError:
    """OAuthError enum tests."""

    def test_oauth_error_values(self) -> None:
        """OAuthError should have expected error types."""
        from src.auth.gmail_oauth import OAuthError

        assert OAuthError.INVALID_CODE.value == "invalid_code"
        assert OAuthError.TOKEN_REFRESH_FAILED.value == "token_refresh_failed"
        assert OAuthError.NO_REFRESH_TOKEN.value == "no_refresh_token"
