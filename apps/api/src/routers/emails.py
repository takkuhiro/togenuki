"""Email API endpoints."""

import google.auth
from fastapi import APIRouter, Depends
from google.cloud.storage import Client as StorageClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.gmail_oauth import GmailOAuthService
from src.auth.middleware import get_current_user
from src.auth.schemas import FirebaseUser
from src.config import get_settings
from src.database import get_db
from src.repositories.email_repository import (
    get_emails_by_user_id,
    get_user_by_firebase_uid,
)
from src.schemas.email import EmailDTO, EmailsResponse
from src.services.gmail_service import GmailApiClient
from src.services.reply_sync_service import ReplySyncService
from src.utils.gcs_signer import extract_blob_path, generate_signed_url
from src.utils.logging import get_logger

logger = get_logger(__name__)

_storage_client: StorageClient | None = None


def _get_storage_client() -> StorageClient:
    """Get or create a module-level storage client.

    Uses cloud-platform scope so the credentials can also call
    IAM signBlob API for generating signed URLs.
    """
    global _storage_client
    if _storage_client is None:
        credentials, project = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        _storage_client = StorageClient(credentials=credentials, project=project)
    return _storage_client


def _resolve_audio_url(audio_url: str | None) -> str | None:
    """Convert a blob path or legacy public URL to a signed URL.

    Args:
        audio_url: The stored audio_url (blob path or legacy public URL)

    Returns:
        A signed URL string, or None if audio_url is None/empty
    """
    if not audio_url:
        return None

    settings = get_settings()
    blob_path = extract_blob_path(audio_url, settings.gcs_bucket_name)
    if blob_path is None:
        return None

    client = _get_storage_client()
    return generate_signed_url(client, settings.gcs_bucket_name, blob_path)


router = APIRouter()


async def run_reply_sync(session: AsyncSession, firebase_uid: str) -> None:
    """Run reply sync for a user. Errors are logged and swallowed."""
    user = await get_user_by_firebase_uid(session, firebase_uid)
    if not user or not user.gmail_refresh_token:
        return

    oauth_service = GmailOAuthService()
    token_result = await oauth_service.ensure_valid_access_token(
        current_token=user.gmail_access_token,
        expires_at=user.gmail_token_expires_at,
        refresh_token=user.gmail_refresh_token,
    )
    if not token_result:
        return

    gmail_client = GmailApiClient(token_result["access_token"])
    sync_service = ReplySyncService()
    updated = await sync_service.sync_reply_status(session, user, gmail_client)
    if updated > 0:
        logger.info(f"Reply sync: updated {updated} emails for user {firebase_uid}")


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
            "sender_name": (
                email.contact.contact_name
                if email.contact and email.contact.contact_name
                else email.sender_name
            ),
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
            "reply_source": email.reply_source,
            "composed_body": email.composed_body,
            "composed_subject": email.composed_subject,
            "google_draft_id": email.google_draft_id,
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
    Runs reply sync in the background before returning.

    Args:
        user: Authenticated Firebase user
        session: Database session

    Returns:
        EmailsResponse with list of emails and total count
    """
    try:
        await run_reply_sync(session, user.uid)
    except Exception:
        logger.exception("Reply sync failed, continuing with email fetch")

    emails_data = await get_user_emails(session, user.uid)

    email_dtos = [
        EmailDTO(
            id=email["id"],
            senderName=email["sender_name"],
            senderEmail=email["sender_email"],
            subject=email["subject"],
            convertedBody=email["converted_body"],
            audioUrl=_resolve_audio_url(email["audio_url"]),
            isProcessed=email["is_processed"],
            receivedAt=email["received_at"],
            repliedAt=email["replied_at"],
            replyBody=email["reply_body"],
            replySubject=email["reply_subject"],
            replySource=email["reply_source"],
            composedBody=email["composed_body"],
            composedSubject=email["composed_subject"],
            googleDraftId=email["google_draft_id"],
        )
        for email in emails_data
    ]

    return EmailsResponse(emails=email_dtos, total=len(email_dtos))
