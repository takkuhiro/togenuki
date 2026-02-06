"""Learning Service for Contact Pattern Analysis.

This service orchestrates the learning process:
- Fetches past emails from Gmail API
- Analyzes patterns using Gemini API
- Saves results to contact_context
- Updates learning status
"""

from datetime import datetime, timezone
from uuid import UUID

from src.auth.gmail_oauth import GmailOAuthService
from src.database import get_db
from src.repositories.contact_repository import (
    create_contact_context,
    get_contact_by_id,
    get_user_by_id,
    update_contact_learning_status,
)
from src.services.gemini_service import GeminiService
from src.services.gmail_service import (
    GmailApiClient,
    GmailApiError,
    parse_gmail_message,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)

MAX_RETRIES = 3
MAX_EMAILS = 30


class LearningService:
    """Service for learning contact patterns from email history."""

    async def process_learning(
        self,
        contact_id: UUID,
        user_id: UUID,
    ) -> None:
        """Execute learning process for a contact.

        1. Get contact and user from DB
        2. Fetch past emails using Gmail API
        3. Analyze patterns using Gemini
        4. Save results to contact_context
        5. Update is_learning_complete flag

        Args:
            contact_id: The contact's ID
            user_id: The user's ID
        """
        async for session in get_db():
            try:
                # Get user and contact
                user = await get_user_by_id(session, user_id)
                if user is None:
                    logger.warning(f"User not found: {user_id}")
                    return

                contact = await get_contact_by_id(session, contact_id)
                if contact is None:
                    logger.warning(f"Contact not found: {contact_id}")
                    return

                # Ensure valid access token (refresh if expired)
                oauth_service = GmailOAuthService()
                token_result = await oauth_service.ensure_valid_access_token(
                    current_token=user.gmail_access_token,
                    expires_at=user.gmail_token_expires_at,
                    refresh_token=user.gmail_refresh_token,
                )

                if token_result is None:
                    logger.warning(f"User {user_id} has no valid Gmail access token")
                    await update_contact_learning_status(
                        session=session,
                        contact_id=contact_id,
                        is_complete=False,
                        failed_at=datetime.now(timezone.utc),
                    )
                    await session.commit()
                    return

                access_token = token_result["access_token"]

                # Update stored token if it was refreshed
                if access_token != user.gmail_access_token:
                    user.gmail_access_token = access_token
                    user.gmail_token_expires_at = token_result["expires_at"]
                    await session.commit()

                # Fetch emails from Gmail
                try:
                    email_history = await self._fetch_email_history(
                        access_token=access_token,
                        gmail_query=contact.gmail_query
                        or f"from:{contact.contact_email}",
                    )
                except GmailApiError as e:
                    logger.error(f"Gmail API error for contact {contact_id}: {e}")
                    await update_contact_learning_status(
                        session=session,
                        contact_id=contact_id,
                        is_complete=False,
                        failed_at=datetime.now(timezone.utc),
                    )
                    await session.commit()
                    return

                if not email_history:
                    logger.warning(f"No emails found for contact {contact_id}")
                    # Still mark as complete, just with no patterns
                    await create_contact_context(
                        session=session,
                        contact_id=contact_id,
                        learned_patterns='{"contactCharacteristics": {}, "userReplyPatterns": {}}',
                    )
                    await update_contact_learning_status(
                        session=session,
                        contact_id=contact_id,
                        is_complete=True,
                    )
                    await session.commit()
                    return

                # Analyze patterns with Gemini (with retries)
                gemini_service = GeminiService()
                learned_patterns = None

                for attempt in range(MAX_RETRIES):
                    result = await gemini_service.analyze_patterns(
                        contact_name=contact.contact_name or contact.contact_email,
                        email_history=email_history,
                    )

                    if result.is_ok():
                        learned_patterns = result.unwrap()
                        break
                    else:
                        logger.warning(
                            f"Gemini analysis failed for contact {contact_id}, "
                            f"attempt {attempt + 1}/{MAX_RETRIES}: {result.unwrap_err()}"
                        )

                if learned_patterns is None:
                    logger.error(
                        f"Gemini analysis failed after {MAX_RETRIES} retries for contact {contact_id}"
                    )
                    await update_contact_learning_status(
                        session=session,
                        contact_id=contact_id,
                        is_complete=False,
                        failed_at=datetime.now(timezone.utc),
                    )
                    await session.commit()
                    return

                # Save contact context
                await create_contact_context(
                    session=session,
                    contact_id=contact_id,
                    learned_patterns=learned_patterns,
                )

                # Update learning status
                await update_contact_learning_status(
                    session=session,
                    contact_id=contact_id,
                    is_complete=True,
                )

                await session.commit()
                logger.info(f"Learning completed for contact {contact_id}")

            except Exception as e:
                logger.exception(
                    f"Unexpected error in learning process for contact {contact_id}: {e}"
                )
                try:
                    await update_contact_learning_status(
                        session=session,
                        contact_id=contact_id,
                        is_complete=False,
                        failed_at=datetime.now(timezone.utc),
                    )
                    await session.commit()
                except Exception:
                    pass
                return

    async def _fetch_email_history(
        self,
        access_token: str,
        gmail_query: str,
    ) -> list[dict]:
        """Fetch email history from Gmail API.

        Args:
            access_token: Gmail API access token
            gmail_query: Gmail search query

        Returns:
            List of email data dicts

        Raises:
            GmailApiError: If API call fails
        """
        gmail_client = GmailApiClient(access_token)

        # Search for messages
        messages = await gmail_client.search_messages(
            query=gmail_query,
            max_results=MAX_EMAILS,
        )

        if not messages:
            return []

        # Fetch each message
        email_history = []
        for msg_meta in messages:
            try:
                message = await gmail_client.fetch_message(msg_meta["id"])
                parsed = parse_gmail_message(message)
                email_history.append(
                    {
                        "sender": parsed["sender_email"],
                        "body": parsed["original_body"],
                        "user_reply": None,  # TODO: Fetch user's reply if available
                    }
                )
            except GmailApiError as e:
                logger.warning(f"Failed to fetch message {msg_meta['id']}: {e}")
                continue

        return email_history
