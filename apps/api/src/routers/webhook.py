"""Gmail Pub/Sub Webhook Handler.

Receives push notifications from Google Cloud Pub/Sub when new emails arrive
in Gmail. Immediately returns 200 OK and processes the notification
asynchronously using BackgroundTasks.
"""

import base64
import json

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from src.database import get_db
from src.services.email_processor import EmailProcessorService
from src.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

# In-memory cache for duplicate detection
# In production, use Redis or database for persistence across instances
_processed_history_ids: set[str] = set()
_MAX_HISTORY_CACHE_SIZE = 1000


class PubSubData(BaseModel):
    """Pub/Sub message data fields."""

    data: str | None = None
    messageId: str
    publishTime: str


class PubSubMessage(BaseModel):
    """Pub/Sub push message format."""

    message: PubSubData
    subscription: str


class GmailNotificationData(BaseModel):
    """Decoded Gmail notification data."""

    emailAddress: str
    historyId: int | str  # Gmail API sends this as int

    @property
    def history_id_str(self) -> str:
        """Return historyId as string."""
        return str(self.historyId)


def is_duplicate_notification(email: str, history_id: str) -> bool:
    """Check if this notification has already been processed.

    Uses in-memory cache for historyId deduplication.
    In production, this should use Redis or database.

    Args:
        email: The user's email address
        history_id: Gmail history ID from the notification

    Returns:
        True if this notification is a duplicate, False otherwise
    """
    cache_key = f"{email}:{history_id}"

    if cache_key in _processed_history_ids:
        logger.info(f"Duplicate notification detected: {cache_key}")
        return True

    # Add to cache, with basic size management
    if len(_processed_history_ids) >= _MAX_HISTORY_CACHE_SIZE:
        # Remove oldest entries (simple strategy - in production use LRU)
        _processed_history_ids.clear()

    _processed_history_ids.add(cache_key)
    return False


async def process_gmail_notification(email: str, history_id: str) -> None:
    """Process Gmail notification in background.

    This function is called asynchronously after returning 200 OK to Pub/Sub.
    It fetches new emails and triggers the processing pipeline.

    Args:
        email: The user's email address
        history_id: Gmail history ID to fetch changes from
    """
    logger.info(
        f"[BACKGROUND] Starting background processing for {email}, historyId={history_id}"
    )

    # Create a new database session for background task
    async for session in get_db():
        try:
            logger.info("[BACKGROUND] Created database session, initializing processor")
            processor = EmailProcessorService(session)
            result = await processor.process_notification(email, history_id)

            if result.skipped:
                logger.info(
                    f"[BACKGROUND] Notification processing skipped: {result.reason}"
                )
            else:
                logger.info(
                    f"[BACKGROUND] Notification processed: {result.processed_count} emails processed, "
                    f"{result.skipped_count} skipped"
                )
        except Exception as e:
            logger.exception(
                f"[BACKGROUND] Error in background notification processing: {e}"
            )
        finally:
            logger.info("[BACKGROUND] Closing database session")
            await session.close()


def decode_pubsub_data(encoded_data: str) -> GmailNotificationData:
    """Decode base64-encoded Pub/Sub message data.

    Args:
        encoded_data: Base64-encoded JSON string

    Returns:
        Decoded GmailNotificationData

    Raises:
        ValueError: If decoding or parsing fails
    """
    try:
        decoded_bytes = base64.b64decode(encoded_data)
        decoded_json = json.loads(decoded_bytes.decode("utf-8"))
        return GmailNotificationData(**decoded_json)
    except Exception as e:
        raise ValueError(f"Failed to decode Pub/Sub data: {e}") from e


@router.post("/gmail")
async def handle_gmail_webhook(
    payload: PubSubMessage,
    background_tasks: BackgroundTasks,
) -> dict:
    """Handle Gmail Pub/Sub push notification.

    This endpoint receives push notifications from Google Cloud Pub/Sub
    when new emails arrive in a user's Gmail inbox. It immediately returns
    200 OK to acknowledge receipt, then processes the notification
    asynchronously.

    Pub/Sub expects a response within 10 seconds, so we return immediately
    and handle the email processing in a background task.

    Args:
        payload: The Pub/Sub push message
        background_tasks: FastAPI BackgroundTasks for async processing

    Returns:
        Status acknowledgment

    Raises:
        HTTPException: 400 if message data is invalid
    """
    # Validate that data field exists
    if not payload.message.data:
        logger.warning("Received Pub/Sub message without data field")
        raise HTTPException(
            status_code=400, detail="Missing data field in Pub/Sub message"
        )

    # Decode the message data
    logger.info("[WEBHOOK] Received Pub/Sub message, decoding data...")
    try:
        notification = decode_pubsub_data(payload.message.data)
        logger.info(
            f"[WEBHOOK] Decoded: email={notification.emailAddress}, historyId={notification.historyId}"
        )
    except ValueError as e:
        logger.warning(f"[WEBHOOK] Invalid Pub/Sub message data: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e

    # Convert historyId to string
    history_id = str(notification.historyId)

    # Check for duplicate notifications
    if is_duplicate_notification(notification.emailAddress, history_id):
        logger.info(
            f"[WEBHOOK] Skipping duplicate notification for {notification.emailAddress}"
        )
        return {"status": "accepted"}

    # Add processing to background tasks
    logger.info(f"[WEBHOOK] Adding background task for {notification.emailAddress}")
    background_tasks.add_task(
        process_gmail_notification, notification.emailAddress, history_id
    )

    logger.info(
        f"[WEBHOOK] Gmail notification queued for processing: "
        f"email={notification.emailAddress}, historyId={history_id}"
    )

    return {"status": "accepted"}
