"""Email Processing Orchestration Service.

Handles the complete email processing pipeline:
1. Fetch new emails from Gmail API based on Pub/Sub notification
2. Validate sender against registered contacts
3. Store email in database
4. Convert to gyaru style using Gemini
5. Generate audio using Cloud TTS
"""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.gmail_oauth import GmailOAuthService
from src.models import Email, User
from src.repositories.email_repository import (
    create_email_record,
    email_exists,
    get_contact_for_email,
)
from src.services.gemini_service import GeminiService
from src.services.gmail_service import (
    GmailApiClient,
    GmailApiError,
    parse_gmail_message,
)
from src.services.tts_service import TTSService
from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class NotificationResult:
    """Result of processing a Gmail notification."""

    skipped: bool = False
    reason: str | None = None
    processed_count: int = 0
    skipped_count: int = 0


@dataclass
class MessageResult:
    """Result of processing a single email message."""

    processed: bool = False
    reason: str | None = None
    email_id: UUID | None = None


class EmailProcessorService:
    """Service for processing email notifications and messages."""

    def __init__(self, session: AsyncSession):
        """Initialize processor with database session.

        Args:
            session: Async database session
        """
        self.session = session
        self.oauth_service = GmailOAuthService()
        self.gemini_service = GeminiService()
        self.tts_service = TTSService()

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
        logger.info(f"Processing notification for {email_address}")
        try:
            # 1. Look up user by email
            user = await self._get_user_by_email(email_address)
            if not user:
                logger.warning(f"User not found for email: {email_address}")
                return NotificationResult(skipped=True, reason="User not found")
            logger.debug(f"Found user: id={user.id}")

            # 2. Check if user has Gmail connected
            if not user.gmail_refresh_token:
                logger.warning(f"User {user.id} has no Gmail OAuth token")
                return NotificationResult(skipped=True, reason="Gmail not connected")

            # 3. Check if user has stored historyId from Gmail Watch setup
            if not user.gmail_history_id:
                logger.warning(f"User {user.id} has no stored gmail_history_id")
                return NotificationResult(
                    skipped=True, reason="Gmail watch not set up (no stored historyId)"
                )
            stored_history_id = user.gmail_history_id
            logger.debug(
                f"Stored historyId: {stored_history_id}, "
                f"notification historyId: {history_id}"
            )

            # 4. Skip if notification's historyId is older than stored (already processed)
            try:
                if int(history_id) <= int(stored_history_id):
                    logger.debug(
                        f"Notification historyId {history_id} <= stored {stored_history_id}, "
                        "skipping (already processed)"
                    )
                    return NotificationResult(
                        skipped=True,
                        reason="Already processed (notification historyId <= stored historyId)",
                    )
            except ValueError:
                logger.warning("Could not compare historyIds as integers, continuing")

            # 5. Get valid access token
            access_token = await self._get_valid_access_token(user)
            if not access_token:
                logger.error(f"Failed to get access token for user {user.id}")
                return NotificationResult(
                    skipped=True, reason="Failed to get access token"
                )

            # 6. Fetch and process new messages using stored historyId
            return await self._fetch_and_process_messages(
                user, access_token, stored_history_id
            )

        except Exception as e:
            logger.exception(f"Error processing notification: {e}")
            return NotificationResult(
                skipped=True, reason=f"Processing error: {str(e)}"
            )

    async def _process_single_message(
        self,
        user_id: UUID,
        gmail_message: dict,
    ) -> MessageResult:
        """Process a single Gmail message.

        Args:
            user_id: The user's database ID
            gmail_message: Raw Gmail API message response

        Returns:
            MessageResult with processing status
        """
        try:
            # Parse the message
            email_data = parse_gmail_message(gmail_message)
            sender_email = email_data["sender_email"]
            google_message_id = email_data["google_message_id"]

            # 1. Check if sender is a registered contact
            contact = await get_contact_for_email(self.session, user_id, sender_email)
            if not contact:
                logger.debug(
                    f"Skipping message from unregistered contact: {sender_email}"
                )
                return MessageResult(
                    processed=False, reason="Sender not registered as contact"
                )

            # 2. Check if email already exists
            if await email_exists(self.session, google_message_id):
                logger.debug(f"Email already exists: {google_message_id}")
                return MessageResult(processed=False, reason="Email already exists")

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

            # 4. Trigger AI conversion (Gemini) and TTS
            await self._process_ai_conversion(email, email_data)

            return MessageResult(processed=True, email_id=email.id)

        except Exception as e:
            logger.exception(f"Error processing message: {e}")
            return MessageResult(processed=False, reason=f"Processing error: {str(e)}")

    async def _process_ai_conversion(
        self,
        email: "Email",
        email_data: dict,
    ) -> None:
        """Process AI conversion (Gemini) and TTS for an email.

        Args:
            email: Email model instance
            email_data: Parsed email data dict
        """

        sender_name = email_data.get("sender_name") or email_data.get(
            "sender_email", ""
        )
        original_body = email_data.get("original_body") or ""

        # Skip AI processing if no body
        if not original_body.strip():
            logger.warning(f"Email {email.id} has no body, skipping AI conversion")
            return

        # 1. Convert to gyaru style using Gemini
        gemini_result = await self.gemini_service.convert_to_gyaru(
            sender_name=sender_name,
            original_body=original_body,
        )

        if gemini_result.is_err():
            logger.error(
                f"Gemini conversion failed for email {email.id}: {gemini_result.unwrap_err()}"
            )
            return

        converted_body = gemini_result.unwrap()
        email.converted_body = converted_body
        logger.info(f"Email {email.id} converted to gyaru style")

        # 2. Generate audio using TTS
        tts_result = await self.tts_service.synthesize_and_upload(
            text=converted_body,
            email_id=email.id,
        )

        if tts_result.is_err():
            logger.error(
                f"TTS synthesis failed for email {email.id}: {tts_result.unwrap_err()}"
            )
            return

        audio_url = tts_result.unwrap()
        email.audio_url = audio_url
        email.is_processed = True
        logger.info(f"Email {email.id} audio generated: {audio_url}")

    async def _get_user_by_email(self, email_address: str) -> User | None:
        """Fetch user by email address.

        Args:
            email_address: User's email address

        Returns:
            User if found, None otherwise
        """
        query = select(User).where(User.email == email_address)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_valid_access_token(self, user: User) -> str | None:
        """Get a valid Gmail access token for the user.

        Refreshes the token if expired.

        Args:
            user: User model with OAuth tokens

        Returns:
            Valid access token or None if refresh fails
        """
        result = await self.oauth_service.ensure_valid_access_token(
            current_token=user.gmail_access_token,
            expires_at=user.gmail_token_expires_at,
            refresh_token=user.gmail_refresh_token,
        )

        if not result:
            return None

        # Update user's tokens if they were refreshed
        if result["access_token"] != user.gmail_access_token:
            user.gmail_access_token = result["access_token"]
            user.gmail_token_expires_at = result["expires_at"]
            await self.session.commit()

        return result["access_token"]

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

            # Fetch history using stored historyId
            logger.debug(f"Fetching email history, startHistoryId={history_id}")
            history = await client.fetch_email_history(history_id)

            # Get the latest historyId from response for updating user record
            latest_history_id = history.get("historyId")

            # Extract message IDs from history
            message_ids = self._extract_message_ids(history)
            logger.debug(f"Extracted {len(message_ids)} message IDs from history")

            if not message_ids:
                logger.debug("No new messages in history")
                if latest_history_id:
                    user.gmail_history_id = latest_history_id
                    await self.session.commit()
                return NotificationResult(
                    skipped=False,
                    processed_count=0,
                    skipped_count=0,
                )

            # Process each message
            for message_id in message_ids:
                try:
                    message = await client.fetch_message(message_id)
                    result = await self._process_single_message(user.id, message)

                    if result.processed:
                        processed_count += 1
                    else:
                        skipped_count += 1
                        logger.debug(f"Message {message_id} skipped: {result.reason}")

                except GmailApiError as e:
                    logger.error(f"Failed to fetch message {message_id}: {e}")
                    skipped_count += 1

            # Update user's gmail_history_id with the latest historyId
            if latest_history_id:
                user.gmail_history_id = latest_history_id

            await self.session.commit()

            logger.info(
                f"Notification processed: {processed_count} emails processed, "
                f"{skipped_count} skipped"
            )

            return NotificationResult(
                skipped=False,
                processed_count=processed_count,
                skipped_count=skipped_count,
            )

        except GmailApiError as e:
            logger.error(f"Gmail API error: {e}")
            return NotificationResult(skipped=True, reason=f"Gmail API error: {str(e)}")

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
