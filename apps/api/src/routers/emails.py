"""Email API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.auth.schemas import FirebaseUser
from src.database import get_db
from src.repositories.email_repository import (
    get_emails_by_user_id,
    get_user_by_firebase_uid,
)
from src.schemas.email import EmailDTO, EmailsResponse

router = APIRouter()


async def get_user_emails(
    session: AsyncSession,
    firebase_uid: str,
) -> list[dict]:
    """Get emails for a user by their Firebase UID.

    Args:
        session: Database session
        firebase_uid: The user's Firebase UID

    Returns:
        List of email dictionaries with camelCase keys
    """
    user = await get_user_by_firebase_uid(session, firebase_uid)
    if user is None:
        return []

    emails = await get_emails_by_user_id(session, user.id)

    return [
        {
            "id": str(email.id),
            "sender_name": email.sender_name,
            "sender_email": email.sender_email,
            "subject": email.subject,
            "converted_body": email.converted_body,
            "audio_url": email.audio_url,
            "is_processed": email.is_processed,
            "received_at": (
                email.received_at.isoformat() if email.received_at else None
            ),
            "replied_at": (email.replied_at.isoformat() if email.replied_at else None),
            "reply_body": email.reply_body,
            "reply_subject": email.reply_subject,
        }
        for email in emails
    ]


@router.get("/emails", response_model=EmailsResponse)
async def get_emails(
    user: FirebaseUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmailsResponse:
    """Get all emails for the authenticated user.

    Returns emails sorted by received_at in descending order (newest first).

    Args:
        user: Authenticated Firebase user
        session: Database session

    Returns:
        EmailsResponse with list of emails and total count
    """
    emails_data = await get_user_emails(session, user.uid)

    email_dtos = [
        EmailDTO(
            id=email["id"],
            senderName=email["sender_name"],
            senderEmail=email["sender_email"],
            subject=email["subject"],
            convertedBody=email["converted_body"],
            audioUrl=email["audio_url"],
            isProcessed=email["is_processed"],
            receivedAt=email["received_at"],
            repliedAt=email["replied_at"],
            replyBody=email["reply_body"],
            replySubject=email["reply_subject"],
        )
        for email in emails_data
    ]

    return EmailsResponse(emails=email_dtos, total=len(email_dtos))
