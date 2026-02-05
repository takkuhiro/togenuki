"""Gmail OAuth service for managing OAuth tokens."""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import TypedDict
from urllib.parse import urlencode

import httpx

from src.config import get_settings


class OAuthError(str, Enum):
    """OAuth error types."""

    INVALID_CODE = "invalid_code"
    TOKEN_REFRESH_FAILED = "token_refresh_failed"
    NO_REFRESH_TOKEN = "no_refresh_token"


class OAuthTokens(TypedDict):
    """OAuth token response structure."""

    access_token: str
    refresh_token: str
    expires_at: datetime


class RefreshedToken(TypedDict):
    """Refreshed access token response structure."""

    access_token: str
    expires_at: datetime


# OAuth configuration
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


class GmailOAuthService:
    """Service for handling Gmail OAuth authentication."""

    def __init__(self) -> None:
        """Initialize Gmail OAuth service."""
        self._settings = get_settings()

    def get_authorization_url(self, state: str) -> str:
        """
        Generate OAuth authorization URL.

        Args:
            state: CSRF protection state parameter.

        Returns:
            Authorization URL for Google OAuth.
        """
        params = {
            "client_id": self._settings.google_client_id,
            "redirect_uri": self._settings.google_redirect_uri,
            "response_type": "code",
            "scope": " ".join(GMAIL_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> OAuthTokens | None:
        """
        Exchange authorization code for access and refresh tokens.

        Args:
            code: Authorization code from OAuth callback.

        Returns:
            OAuthTokens on success, None on failure.
        """
        data = {
            "client_id": self._settings.google_client_id,
            "client_secret": self._settings.google_client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self._settings.google_redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=data)

        if response.status_code != 200:
            return None

        token_data = response.json()
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        return OAuthTokens(
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token", ""),
            expires_at=expires_at,
        )

    async def refresh_access_token(self, refresh_token: str) -> RefreshedToken | None:
        """
        Refresh access token using refresh token.

        Args:
            refresh_token: OAuth refresh token.

        Returns:
            RefreshedToken on success, None on failure.
        """
        data = {
            "client_id": self._settings.google_client_id,
            "client_secret": self._settings.google_client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(GOOGLE_TOKEN_URL, data=data)

        if response.status_code != 200:
            return None

        token_data = response.json()
        expires_in = token_data.get("expires_in", 3600)
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        return RefreshedToken(
            access_token=token_data["access_token"],
            expires_at=expires_at,
        )

    def is_token_expired(self, expires_at: datetime | None) -> bool:
        """
        Check if access token is expired.

        Args:
            expires_at: Token expiration datetime.

        Returns:
            True if token is expired or expires_at is None.
        """
        if expires_at is None:
            return True

        # Add 5 minute buffer for safety
        buffer = timedelta(minutes=5)
        return datetime.now(timezone.utc) >= (expires_at - buffer)

    async def ensure_valid_access_token(
        self,
        current_token: str | None,
        expires_at: datetime | None,
        refresh_token: str | None,
    ) -> RefreshedToken | None:
        """
        Ensure a valid access token is available.

        Returns the current token if still valid, or refreshes it if expired.

        Args:
            current_token: Current access token (may be expired).
            expires_at: Current token expiration datetime.
            refresh_token: Refresh token for obtaining new access token.

        Returns:
            RefreshedToken with valid access token and expiration,
            or None if refresh fails or no refresh token is available.
        """
        # Check if current token is still valid
        if current_token and expires_at and not self.is_token_expired(expires_at):
            return RefreshedToken(
                access_token=current_token,
                expires_at=expires_at,
            )

        # Need to refresh token
        if not refresh_token:
            return None

        return await self.refresh_access_token(refresh_token)
