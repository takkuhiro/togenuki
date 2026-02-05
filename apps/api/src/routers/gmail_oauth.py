"""Gmail OAuth API endpoints."""

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.gmail_oauth import GmailOAuthService, OAuthError
from src.auth.middleware import get_current_user
from src.auth.schemas import FirebaseUser
from src.database import get_db
from src.models import User

router = APIRouter(tags=["Gmail OAuth"])


class AuthUrlResponse(BaseModel):
    """Response for OAuth URL endpoint."""

    url: str


class CallbackRequest(BaseModel):
    """Request body for OAuth callback."""

    code: str


class CallbackResponse(BaseModel):
    """Response for OAuth callback endpoint."""

    success: bool


class StatusResponse(BaseModel):
    """Response for Gmail connection status endpoint."""

    connected: bool
    has_refresh_token: bool = False
    has_access_token: bool = False
    token_expires_at: str | None = None


@router.get("/url", response_model=AuthUrlResponse)
async def get_gmail_auth_url(
    current_user: FirebaseUser = Depends(get_current_user),
) -> AuthUrlResponse:
    """
    Get Gmail OAuth authorization URL.

    Returns a URL to redirect the user to for Gmail OAuth consent.
    """
    service = GmailOAuthService()
    # Generate state with user's firebase_uid for CSRF protection
    state = f"{current_user.uid}:{secrets.token_urlsafe(16)}"
    url = service.get_authorization_url(state)

    return AuthUrlResponse(url=url)


@router.post("/callback", response_model=CallbackResponse)
async def gmail_oauth_callback(
    request: CallbackRequest,
    current_user: FirebaseUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CallbackResponse:
    """
    Handle Gmail OAuth callback.

    Exchanges the authorization code for tokens and stores them.
    """
    service = GmailOAuthService()
    tokens = await service.exchange_code_for_tokens(request.code)

    if tokens is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": OAuthError.INVALID_CODE.value},
        )

    # Check if user exists
    stmt = select(User).where(User.firebase_uid == current_user.uid)
    result = await db.execute(stmt)
    user: User | None = result.scalar_one_or_none()

    if user is None:
        # Create new user with Gmail tokens
        user = User(
            firebase_uid=current_user.uid,
            email=current_user.email,
            gmail_access_token=tokens["access_token"],
            gmail_refresh_token=tokens["refresh_token"],
            gmail_token_expires_at=tokens["expires_at"],
        )
        db.add(user)
    else:
        # Update existing user with Gmail tokens
        user.gmail_access_token = tokens["access_token"]
        user.gmail_refresh_token = tokens["refresh_token"]
        user.gmail_token_expires_at = tokens["expires_at"]

    await db.commit()

    return CallbackResponse(success=True)


@router.get("/status", response_model=StatusResponse)
async def get_gmail_status(
    current_user: FirebaseUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatusResponse:
    """
    Check Gmail connection status.

    Returns whether the user has connected their Gmail account.
    """
    stmt = select(User).where(User.firebase_uid == current_user.uid)
    result = await db.execute(stmt)
    user: User | None = result.scalar_one_or_none()

    if user is None:
        return StatusResponse(connected=False)

    connected = user.gmail_refresh_token is not None
    return StatusResponse(
        connected=connected,
        has_refresh_token=user.gmail_refresh_token is not None,
        has_access_token=user.gmail_access_token is not None,
        token_expires_at=user.gmail_token_expires_at.isoformat()
        if user.gmail_token_expires_at
        else None,
    )
