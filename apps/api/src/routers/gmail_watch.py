"""Gmail Watch API endpoints.

Provides endpoints to set up and manage Gmail push notifications.
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.gmail_oauth import GmailOAuthService
from src.auth.middleware import get_current_user
from src.auth.schemas import FirebaseUser
from src.database import get_db
from src.models import User
from src.services.gmail_watch import GmailWatchService
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


class WatchResponse(BaseModel):
    """Response model for Gmail watch operations."""

    success: bool
    history_id: str | None = None
    expiration: datetime | None = None
    error: str | None = None


class WatchStatusResponse(BaseModel):
    """Response model for Gmail watch status."""

    is_watching: bool
    expiration: datetime | None = None


async def get_user_from_db(
    firebase_user: FirebaseUser,
    session: AsyncSession,
) -> User:
    """Get user from database by Firebase UID."""
    from sqlalchemy import select

    query = select(User).where(User.firebase_uid == firebase_user.uid)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@router.post("/watch", response_model=WatchResponse)
async def setup_gmail_watch(
    firebase_user: FirebaseUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WatchResponse:
    """Set up Gmail push notifications for the authenticated user.

    This endpoint configures Gmail to send push notifications to our
    Pub/Sub topic whenever new emails arrive in the user's inbox.

    Gmail watch expires after 7 days and needs to be renewed.

    Returns:
        WatchResponse with success status and watch details
    """
    # Get user from database
    user = await get_user_from_db(firebase_user, session)

    # Check if user has Gmail connected
    if not user.gmail_refresh_token:
        raise HTTPException(
            status_code=400,
            detail="Gmail not connected. Please complete Gmail OAuth first.",
        )

    # Get valid access token
    oauth_service = GmailOAuthService()
    token_result = await oauth_service.ensure_valid_access_token(
        current_token=user.gmail_access_token,
        expires_at=user.gmail_token_expires_at,
        refresh_token=user.gmail_refresh_token,
    )

    if not token_result:
        raise HTTPException(
            status_code=401,
            detail="Failed to refresh Gmail access token. Please reconnect Gmail.",
        )

    # Update user's tokens if they were refreshed
    if token_result["access_token"] != user.gmail_access_token:
        user.gmail_access_token = token_result["access_token"]
        user.gmail_token_expires_at = token_result["expires_at"]
        await session.commit()

    # Setup Gmail watch
    watch_service = GmailWatchService()
    watch_result = await watch_service.setup_watch(user.gmail_access_token)

    if watch_result.success:
        # Save history_id to user record for later use in notification processing
        user.gmail_history_id = watch_result.history_id
        await session.commit()
        logger.info(
            f"Gmail watch setup for user {user.id}, historyId={watch_result.history_id}"
        )
        return WatchResponse(
            success=True,
            history_id=watch_result.history_id,
            expiration=watch_result.expiration,
        )
    else:
        logger.error(
            f"Gmail watch setup failed for user {user.id}: {watch_result.error}"
        )
        return WatchResponse(
            success=False,
            error=watch_result.error,
        )


@router.delete("/watch", response_model=WatchResponse)
async def stop_gmail_watch(
    firebase_user: FirebaseUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> WatchResponse:
    """Stop Gmail push notifications for the authenticated user.

    Returns:
        WatchResponse with success status
    """
    # Get user from database
    user = await get_user_from_db(firebase_user, session)

    if not user.gmail_access_token:
        raise HTTPException(status_code=400, detail="Gmail not connected")

    # Stop Gmail watch
    watch_service = GmailWatchService()
    success = await watch_service.stop_watch(user.gmail_access_token)

    if success:
        logger.info(f"Gmail watch stopped for user {user.id}")
        return WatchResponse(success=True)
    else:
        return WatchResponse(success=False, error="Failed to stop Gmail watch")
