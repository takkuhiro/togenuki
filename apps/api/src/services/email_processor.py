"""Email Processing Orchestration Service.

Handles the complete email processing pipeline:
1. Fetch new emails from Gmail API based on Pub/Sub notification
2. Validate sender against registered contacts
3. Store email in database
4. Trigger AI conversion and TTS (placeholder for Phase 4)
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.gmail_oauth import GmailOAuthService
from src.models import Contact, Email, User
from src.services.gmail_service import (
    GmailApiClient,
    GmailApiError,
    create_email_record,
    email_exists,
    get_contact_for_email,
    parse_gmail_message,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class NotificationResult:
    """Result of processing a Gmail notification."""

    skipped: bool = False
    reason: Optional[str] = None
    processed_count: int = 0
    skipped_count: int = 0


@dataclass
class MessageResult:
    """Result of processing a single email message."""

    processed: bool = False
    reason: Optional[str] = None
    email_id: Optional[int] = None


class EmailProcessorService:
    """Service for processing email notifications and messages."""

    def __init__(self, session: AsyncSession):
        """Initialize processor with database session.

        Args:
            session: Async database session
        """
        self.session = session
        self.oauth_service = GmailOAuthService()

    async def process_notification(
        self, email_address: str, history_id: str
    ) -> NotificationResult:
        """Process a Gmail Pub/Sub notification.

        This is the main entry point called from the webhook handler.
        It fetches the user, validates their Gmail connection, and
        processes any new messages.

        Args:
            email_address: User's email address from notification
            history_id: Gmail history ID to fetch changes from

        Returns:
            NotificationResult with processing status
        """
        logger.info(f"[PROCESSOR] Starting notification processing for {email_address}")
        try:
            # 1. Look up user by email
            logger.info(f"[PROCESSOR] Looking up user by email: {email_address}")
            user = await self._get_user_by_email(email_address)
            if not user:
                logger.warning(f"[PROCESSOR] User not found for email: {email_address}")
                return NotificationResult(
                    skipped=True,
                    reason="User not found"
                )
            logger.info(f"[PROCESSOR] Found user: id={user.id}")

            # 2. Check if user has Gmail connected
            if not user.gmail_refresh_token:
                logger.warning(f"[PROCESSOR] User {user.id} has no Gmail OAuth token")
                return NotificationResult(
                    skipped=True,
                    reason="Gmail not connected"
                )
            logger.info(f"[PROCESSOR] User has Gmail refresh token")

            # 3. Get valid access token
            logger.info(f"[PROCESSOR] Getting valid access token for user {user.id}")
            access_token = await self._get_valid_access_token(user)
            if not access_token:
                logger.error(f"[PROCESSOR] Failed to get access token for user {user.id}")
                return NotificationResult(
                    skipped=True,
                    reason="Failed to get access token"
                )
            logger.info(f"[PROCESSOR] Got valid access token")

            # 4. Fetch and process new messages
            logger.info(f"[PROCESSOR] Fetching and processing messages from history {history_id}")
            return await self._fetch_and_process_messages(
                user, access_token, history_id
            )

        except Exception as e:
            logger.exception(f"[PROCESSOR] Error processing notification: {e}")
            return NotificationResult(
                skipped=True,
                reason=f"Processing error: {str(e)}"
            )

    async def process_single_message(
        self,
        user_id: int,
        gmail_message: dict,
        access_token: str,
    ) -> MessageResult:
        """Process a single Gmail message.

        Args:
            user_id: The user's database ID
            gmail_message: Raw Gmail API message response
            access_token: Valid Gmail access token

        Returns:
            MessageResult with processing status
        """
        try:
            # Parse the message
            email_data = parse_gmail_message(gmail_message)
            sender_email = email_data["sender_email"]
            google_message_id = email_data["google_message_id"]

            # 1. Check if sender is a registered contact
            contact = await get_contact_for_email(
                self.session, user_id, sender_email
            )
            if not contact:
                logger.info(
                    f"Skipping message from unregistered contact: {sender_email}"
                )
                return MessageResult(
                    processed=False,
                    reason="Sender not registered as contact"
                )

            # 2. Check if email already exists
            if await email_exists(self.session, google_message_id):
                logger.info(f"Email already exists: {google_message_id}")
                return MessageResult(
                    processed=False,
                    reason="Email already exists"
                )

            # 3. Create email record with is_processed=False
            email = await create_email_record(
                session=self.session,
                user_id=user_id,
                contact_id=contact.id,
                email_data=email_data,
            )

            logger.info(
                f"Created email record: id={email.id}, "
                f"from={sender_email}, subject={email_data.get('subject')}"
            )

            # 4. TODO: Trigger AI conversion and TTS (Phase 4)
            # This will be implemented in Phase 4:
            # - Call GeminiService for gyaru conversion
            # - Call TTSService for audio generation
            # - Update email.converted_body, email.audio_url
            # - Set email.is_processed = True

            return MessageResult(
                processed=True,
                email_id=email.id,
            )

        except Exception as e:
            logger.exception(f"Error processing message: {e}")
            return MessageResult(
                processed=False,
                reason=f"Processing error: {str(e)}"
            )

    async def _get_user_by_email(self, email_address: str) -> Optional[User]:
        """Fetch user by email address.

        Args:
            email_address: User's email address

        Returns:
            User if found, None otherwise
        """
        query = select(User).where(User.email == email_address)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_valid_access_token(self, user: User) -> Optional[str]:
        """Get a valid Gmail access token for the user.

        Refreshes the token if expired.

        Args:
            user: User model with OAuth tokens

        Returns:
            Valid access token or None if refresh fails
        """
        # Check if current token is still valid
        if (
            user.gmail_access_token
            and user.gmail_token_expires_at
            and not self.oauth_service.is_token_expired(user.gmail_token_expires_at)
        ):
            return user.gmail_access_token

        # Need to refresh token
        if not user.gmail_refresh_token:
            return None

        refreshed = await self.oauth_service.refresh_access_token(
            user.gmail_refresh_token
        )
        if not refreshed:
            return None

        # Update user's tokens in database
        user.gmail_access_token = refreshed["access_token"]
        user.gmail_token_expires_at = refreshed["expires_at"]

        await self.session.commit()

        return refreshed["access_token"]

    async def _fetch_and_process_messages(
        self,
        user: User,
        access_token: str,
        history_id: str,
    ) -> NotificationResult:
        """Fetch email history and process new messages.

        Args:
            user: User model
            access_token: Valid Gmail access token
            history_id: Gmail history ID to start from

        Returns:
            NotificationResult with processing statistics
        """
        processed_count = 0
        skipped_count = 0

        try:
            client = GmailApiClient(access_token)

            # Try history API first
            logger.info(f"[PROCESSOR] Fetching email history from Gmail API, historyId={history_id}")
            history = await client.fetch_email_history(history_id)
            logger.info(f"[PROCESSOR] Got history response: {history}")

            # Extract message IDs from history
            message_ids = self._extract_message_ids(history)
            logger.info(f"[PROCESSOR] Extracted {len(message_ids)} message IDs from history: {message_ids}")

            # If history is empty, fallback to listing recent messages
            # This handles the case where notification's historyId is already the latest
            if not message_ids:
                logger.info("[PROCESSOR] History empty, falling back to messages.list API")
                recent_messages = await client.list_recent_messages(max_results=5)
                message_ids = [msg["id"] for msg in recent_messages]
                logger.info(f"[PROCESSOR] Got {len(message_ids)} recent messages: {message_ids}")

            if not message_ids:
                logger.info("[PROCESSOR] No messages to process")
                return NotificationResult(
                    skipped=False,
                    processed_count=0,
                    skipped_count=0,
                )

            # Process each message
            for message_id in message_ids:
                try:
                    # Fetch full message
                    logger.info(f"[PROCESSOR] Fetching message {message_id}")
                    message = await client.fetch_message(message_id)

                    # Process the message
                    result = await self.process_single_message(
                        user.id, message, access_token
                    )

                    if result.processed:
                        processed_count += 1
                        logger.info(f"[PROCESSOR] Message {message_id} processed successfully")
                    else:
                        skipped_count += 1
                        logger.info(f"[PROCESSOR] Message {message_id} skipped: {result.reason}")

                except GmailApiError as e:
                    logger.error(f"[PROCESSOR] Failed to fetch message {message_id}: {e}")
                    skipped_count += 1

            # Commit all changes
            await self.session.commit()
            logger.info(f"[PROCESSOR] Committed all changes")

            return NotificationResult(
                skipped=False,
                processed_count=processed_count,
                skipped_count=skipped_count,
            )

        except GmailApiError as e:
            logger.error(f"[PROCESSOR] Gmail API error: {e}")
            return NotificationResult(
                skipped=True,
                reason=f"Gmail API error: {str(e)}"
            )

    def _extract_message_ids(self, history: dict) -> list[str]:
        """Extract message IDs from Gmail history response.

        Args:
            history: Gmail history API response

        Returns:
            List of message IDs
        """
        message_ids = []
        for history_item in history.get("history", []):
            for msg_added in history_item.get("messagesAdded", []):
                msg = msg_added.get("message", {})
                msg_id = msg.get("id")
                if msg_id:
                    message_ids.append(msg_id)
        return message_ids
