"""Cron endpoints for scheduled tasks.

Called by Cloud Scheduler to perform periodic maintenance.
"""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.gmail_oauth import GmailOAuthService
from src.config import get_settings
from src.database import get_db
from src.models import User
from src.services.gmail_watch import GmailWatchService
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/cron", tags=["cron"])


async def verify_scheduler_secret(
    x_scheduler_secret: str | None = Header(None),
) -> None:
    """Verify the shared secret from Cloud Scheduler."""
    settings = get_settings()
    if not x_scheduler_secret or x_scheduler_secret != settings.scheduler_secret:
        raise HTTPException(status_code=403, detail="Forbidden")


class RenewWatchDetail(BaseModel):
    """Detail of a single user's watch renewal result."""

    user_email: str
    success: bool
    error: str | None = None


class RenewWatchesResponse(BaseModel):
    """Response model for renew-gmail-watches endpoint."""

    total: int
    succeeded: int
    failed: int
    details: list[RenewWatchDetail]


@router.post("/renew-gmail-watches", response_model=RenewWatchesResponse)
async def renew_gmail_watches(
    _: None = Depends(verify_scheduler_secret),
    session: AsyncSession = Depends(get_db),
) -> RenewWatchesResponse:
    """Renew Gmail Watch for all connected users.

    Called by Cloud Scheduler every 6 days to prevent watch expiration.
    Does NOT update gmail_history_id to avoid losing unprocessed emails.
    """
    query = select(User).where(User.gmail_refresh_token.isnot(None))
    result = await session.execute(query)
    users = result.scalars().all()

    details: list[RenewWatchDetail] = []
    succeeded = 0
    failed = 0

    oauth_service = GmailOAuthService()
    watch_service = GmailWatchService()

    for user in users:
        try:
            token_result = await oauth_service.ensure_valid_access_token(
                current_token=user.gmail_access_token,
                expires_at=user.gmail_token_expires_at,
                refresh_token=user.gmail_refresh_token,
            )

            if not token_result:
                failed += 1
                details.append(
                    RenewWatchDetail(
                        user_email=user.email,
                        success=False,
                        error="Failed to refresh access token",
                    )
                )
                continue

            if token_result["access_token"] != user.gmail_access_token:
                user.gmail_access_token = token_result["access_token"]
                user.gmail_token_expires_at = token_result["expires_at"]

            watch_result = await watch_service.setup_watch(token_result["access_token"])

            if watch_result.success:
                succeeded += 1
                details.append(RenewWatchDetail(user_email=user.email, success=True))
            else:
                failed += 1
                details.append(
                    RenewWatchDetail(
                        user_email=user.email,
                        success=False,
                        error=watch_result.error,
                    )
                )

        except Exception as e:
            logger.exception(f"Failed to renew watch for user {user.email}")
            failed += 1
            details.append(
                RenewWatchDetail(
                    user_email=user.email,
                    success=False,
                    error=str(e),
                )
            )

    if users:
        await session.commit()

    return RenewWatchesResponse(
        total=len(users),
        succeeded=succeeded,
        failed=failed,
        details=details,
    )
