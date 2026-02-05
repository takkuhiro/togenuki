"""Gmail Watch Service.

Manages Gmail push notification watch setup and teardown.
Gmail watch allows receiving real-time notifications when new emails arrive.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

import httpx

from src.config import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

settings = get_settings()

GMAIL_API_BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailWatchError(Exception):
    """Exception raised when Gmail Watch API call fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class GmailWatchResult:
    """Result of Gmail watch operation."""

    success: bool
    history_id: Optional[str] = None
    expiration: Optional[datetime] = None
    error: Optional[str] = None


class GmailWatchService:
    """Service for managing Gmail push notification watches."""

    def __init__(self, topic_name: Optional[str] = None):
        """Initialize Gmail Watch service.

        Args:
            topic_name: Pub/Sub topic name for notifications.
                       If not provided, uses default from settings.
        """
        self.topic_name = topic_name or f"projects/{settings.project_id}/topics/gmail-notifications"

    async def setup_watch(self, access_token: str) -> GmailWatchResult:
        """Set up Gmail push notifications.

        Calls Gmail API users.watch to start receiving notifications
        for new emails in the user's inbox.

        Args:
            access_token: Valid Gmail API access token

        Returns:
            GmailWatchResult with success status and watch details
        """
        url = f"{GMAIL_API_BASE_URL}/watch"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "topicName": self.topic_name,
            "labelIds": ["INBOX"],
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, headers=headers, json=payload, timeout=30.0
                )

                if response.status_code == 200:
                    data = response.json()
                    history_id = data.get("historyId")
                    expiration_ms = data.get("expiration")

                    # Convert expiration from milliseconds to datetime
                    expiration = None
                    if expiration_ms:
                        expiration = datetime.fromtimestamp(
                            int(expiration_ms) / 1000, tz=timezone.utc
                        )

                    logger.info(
                        f"Gmail watch setup successful: historyId={history_id}, "
                        f"expires={expiration}"
                    )

                    return GmailWatchResult(
                        success=True,
                        history_id=history_id,
                        expiration=expiration,
                    )
                else:
                    error_msg = f"Gmail watch failed: {response.status_code} - {response.text}"
                    logger.error(error_msg)
                    return GmailWatchResult(
                        success=False,
                        error=error_msg,
                    )

        except Exception as e:
            error_msg = f"Gmail watch error: {str(e)}"
            logger.exception(error_msg)
            return GmailWatchResult(
                success=False,
                error=error_msg,
            )

    async def stop_watch(self, access_token: str) -> bool:
        """Stop Gmail push notifications.

        Args:
            access_token: Valid Gmail API access token

        Returns:
            True if successful, False otherwise
        """
        url = f"{GMAIL_API_BASE_URL}/stop"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, headers=headers, timeout=30.0
                )

                if response.status_code == 204:
                    logger.info("Gmail watch stopped successfully")
                    return True
                else:
                    logger.error(
                        f"Gmail watch stop failed: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            logger.exception(f"Gmail watch stop error: {e}")
            return False
