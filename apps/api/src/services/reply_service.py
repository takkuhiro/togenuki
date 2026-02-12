"""Reply Service for composing and sending reply emails.

Orchestrates the reply flow:
- compose_reply: Fetch email -> get contact_context -> Gemini composition -> subject generation
- send_reply: OAuth token refresh -> Gmail send -> DB update
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from result import Err, Ok, Result
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.gmail_oauth import GmailOAuthService
from src.auth.schemas import FirebaseUser
from src.repositories.email_repository import (
    get_contact_for_email,
    get_email_by_id,
    get_user_by_firebase_uid,
)
from src.services.gemini_service import GeminiService
from src.services.gmail_service import GmailApiClient, GmailApiError, get_message_id
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ReplyError(Enum):
    """Error types for reply operations."""

    EMAIL_NOT_FOUND = "email_not_found"
    UNAUTHORIZED = "unauthorized"
    COMPOSE_FAILED = "compose_failed"
    SEND_FAILED = "send_failed"
    TOKEN_EXPIRED = "token_expired"
    ALREADY_REPLIED = "already_replied"


@dataclass
class ComposeReplyResult:
    """Result of composing a reply email."""

    composed_body: str
    composed_subject: str


@dataclass
class SendReplyResult:
    """Result of sending a reply email."""

    google_message_id: str


class ReplyService:
    """Service for composing and sending reply emails."""

    def __init__(
        self,
        gemini_service: GeminiService | None = None,
        oauth_service: GmailOAuthService | None = None,
        gmail_client_class: type[GmailApiClient] | Any = None,
    ) -> None:
        self.gemini_service = gemini_service or GeminiService()
        self.oauth_service = oauth_service or GmailOAuthService()
        self.gmail_client_class = gmail_client_class or GmailApiClient

    async def compose_reply(
        self,
        session: AsyncSession,
        user: FirebaseUser,
        email_id: UUID,
        raw_text: str,
    ) -> Result[ComposeReplyResult, ReplyError]:
        """Compose a business email reply from casual text.

        Args:
            session: Database session
            user: Authenticated Firebase user
            email_id: ID of the email to reply to
            raw_text: Casual/spoken text from the user

        Returns:
            Result containing ComposeReplyResult or ReplyError
        """
        # 1. Get user from DB
        db_user = await get_user_by_firebase_uid(session, user.uid)
        if not db_user:
            return Err(ReplyError.UNAUTHORIZED)

        # 2. Get email
        email = await get_email_by_id(session, email_id)
        if not email:
            return Err(ReplyError.EMAIL_NOT_FOUND)

        # 3. Verify ownership
        if email.user_id != db_user.id:
            return Err(ReplyError.UNAUTHORIZED)

        # 4. Get contact_context if available
        contact_context: str | None = None
        contact = await get_contact_for_email(session, db_user.id, email.sender_email)
        if contact and contact.context:
            contact_context = contact.context.learned_patterns

        # 5. Call Gemini for business email composition
        sender_name = email.sender_name or email.sender_email
        original_body = email.original_body or ""

        gemini_result = await self.gemini_service.compose_business_reply(
            raw_text=raw_text,
            original_email_body=original_body,
            sender_name=sender_name,
            contact_context=contact_context,
        )

        if gemini_result.is_err():
            logger.error(
                f"Gemini composition failed for email {email_id}: {gemini_result.unwrap_err()}"
            )
            return Err(ReplyError.COMPOSE_FAILED)

        composed_body = gemini_result.unwrap()

        # 6. Generate subject with Re: prefix
        composed_subject = self._generate_reply_subject(email.subject)

        return Ok(
            ComposeReplyResult(
                composed_body=composed_body,
                composed_subject=composed_subject,
            )
        )

    async def send_reply(
        self,
        session: AsyncSession,
        user: FirebaseUser,
        email_id: UUID,
        composed_body: str,
        composed_subject: str,
    ) -> Result[SendReplyResult, ReplyError]:
        """Send a composed reply email via Gmail.

        Args:
            session: Database session
            user: Authenticated Firebase user
            email_id: ID of the email to reply to
            composed_body: The composed email body
            composed_subject: The composed email subject

        Returns:
            Result containing SendReplyResult or ReplyError
        """
        # 1. Get user from DB
        db_user = await get_user_by_firebase_uid(session, user.uid)
        if not db_user:
            return Err(ReplyError.UNAUTHORIZED)

        # 2. Get email
        email = await get_email_by_id(session, email_id)
        if not email:
            return Err(ReplyError.EMAIL_NOT_FOUND)

        # 3. Verify ownership
        if email.user_id != db_user.id:
            return Err(ReplyError.UNAUTHORIZED)

        # 4. Check if already replied
        if email.replied_at is not None:
            return Err(ReplyError.ALREADY_REPLIED)

        # 5. Ensure valid OAuth token
        token_result = await self.oauth_service.ensure_valid_access_token(
            current_token=db_user.gmail_access_token,
            expires_at=db_user.gmail_token_expires_at,
            refresh_token=db_user.gmail_refresh_token,
        )

        if not token_result:
            return Err(ReplyError.TOKEN_EXPIRED)

        access_token = token_result["access_token"]

        # 6. Send email via Gmail API
        try:
            gmail_client = self.gmail_client_class(access_token)

            # Fetch original message to get Message-ID and threadId
            original_message = await gmail_client.fetch_message(email.google_message_id)
            message_id = get_message_id(original_message)
            thread_id = original_message.get("threadId", "")

            in_reply_to = message_id or ""
            references = message_id or ""

            send_result = await gmail_client.send_message(
                to=email.sender_email,
                subject=composed_subject,
                body=composed_body,
                thread_id=thread_id,
                in_reply_to=in_reply_to,
                references=references,
            )
        except GmailApiError as e:
            logger.error(f"Gmail send failed for email {email_id}: {e}")
            return Err(ReplyError.SEND_FAILED)

        # 7. Update DB record
        google_message_id = send_result.get("id", "")
        email.reply_body = composed_body
        email.reply_subject = composed_subject
        email.replied_at = datetime.now(timezone.utc)
        email.reply_google_message_id = google_message_id
        email.reply_source = "togenuki"
        await session.commit()

        return Ok(SendReplyResult(google_message_id=google_message_id))

    @staticmethod
    def _generate_reply_subject(original_subject: str | None) -> str:
        """Generate reply subject with Re: prefix.

        Args:
            original_subject: Original email subject

        Returns:
            Subject with Re: prefix
        """
        if not original_subject:
            return "Re: "

        if original_subject.startswith("Re: "):
            return original_subject

        return f"Re: {original_subject}"
