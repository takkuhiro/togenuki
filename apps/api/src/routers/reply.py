"""Reply API endpoints for composing and sending reply emails.

Provides endpoints for:
- POST /api/emails/{email_id}/compose-reply - Compose business email from casual text
- POST /api/emails/{email_id}/send-reply - Send composed reply email
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.auth.schemas import FirebaseUser
from src.database import get_db
from src.schemas.reply import (
    ComposeReplyRequest,
    ComposeReplyResponse,
    SaveDraftRequest,
    SaveDraftResponse,
    SendReplyRequest,
    SendReplyResponse,
)
from src.services.reply_service import ReplyError, ReplyService

router = APIRouter()

# Error mapping: ReplyError -> HTTP status code
COMPOSE_ERROR_MAP: dict[ReplyError, int] = {
    ReplyError.EMAIL_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ReplyError.UNAUTHORIZED: status.HTTP_403_FORBIDDEN,
    ReplyError.COMPOSE_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
}

SEND_ERROR_MAP: dict[ReplyError, int] = {
    ReplyError.EMAIL_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ReplyError.UNAUTHORIZED: status.HTTP_403_FORBIDDEN,
    ReplyError.SEND_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
    ReplyError.TOKEN_EXPIRED: status.HTTP_503_SERVICE_UNAVAILABLE,
    ReplyError.ALREADY_REPLIED: status.HTTP_409_CONFLICT,
}

DRAFT_ERROR_MAP: dict[ReplyError, int] = {
    ReplyError.EMAIL_NOT_FOUND: status.HTTP_404_NOT_FOUND,
    ReplyError.UNAUTHORIZED: status.HTTP_403_FORBIDDEN,
    ReplyError.DRAFT_FAILED: status.HTTP_503_SERVICE_UNAVAILABLE,
    ReplyError.TOKEN_EXPIRED: status.HTTP_503_SERVICE_UNAVAILABLE,
}


@router.post(
    "/emails/{email_id}/compose-reply",
    response_model=ComposeReplyResponse,
)
async def compose_reply_endpoint(
    email_id: UUID,
    request: ComposeReplyRequest,
    user: FirebaseUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ComposeReplyResponse:
    """Compose a business email reply from casual text.

    Args:
        email_id: ID of the email to reply to
        request: Request body with rawText
        user: Authenticated Firebase user
        session: Database session

    Returns:
        ComposeReplyResponse with composed body and subject

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 404: If email not found
        HTTPException 503: If Gemini API fails
    """
    reply_service = ReplyService()
    result = await reply_service.compose_reply(
        session=session,
        user=user,
        email_id=email_id,
        raw_text=request.rawText,
    )

    if result.is_err():
        error = result.unwrap_err()
        status_code = COMPOSE_ERROR_MAP.get(
            error, status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(
            status_code=status_code,
            detail={"error": error.value},
        )

    compose_result = result.unwrap()
    return ComposeReplyResponse(
        composedBody=compose_result.composed_body,
        composedSubject=compose_result.composed_subject,
    )


@router.post(
    "/emails/{email_id}/send-reply",
    response_model=SendReplyResponse,
)
async def send_reply_endpoint(
    email_id: UUID,
    request: SendReplyRequest,
    user: FirebaseUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SendReplyResponse:
    """Send a composed reply email via Gmail.

    Args:
        email_id: ID of the email to reply to
        request: Request body with composedBody and composedSubject
        user: Authenticated Firebase user
        session: Database session

    Returns:
        SendReplyResponse with success status and Google message ID

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 404: If email not found
        HTTPException 409: If already replied
        HTTPException 503: If Gmail API fails or token expired
    """
    reply_service = ReplyService()
    result = await reply_service.send_reply(
        session=session,
        user=user,
        email_id=email_id,
        composed_body=request.composedBody,
        composed_subject=request.composedSubject,
    )

    if result.is_err():
        error = result.unwrap_err()
        status_code = SEND_ERROR_MAP.get(error, status.HTTP_500_INTERNAL_SERVER_ERROR)
        raise HTTPException(
            status_code=status_code,
            detail={"error": error.value},
        )

    send_result = result.unwrap()
    return SendReplyResponse(
        success=True,
        googleMessageId=send_result.google_message_id,
    )


@router.post(
    "/emails/{email_id}/save-draft",
    response_model=SaveDraftResponse,
)
async def save_draft_endpoint(
    email_id: UUID,
    request: SaveDraftRequest,
    user: FirebaseUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SaveDraftResponse:
    """Save a composed reply email as a Gmail draft.

    Args:
        email_id: ID of the email to reply to
        request: Request body with composedBody and composedSubject
        user: Authenticated Firebase user
        session: Database session

    Returns:
        SaveDraftResponse with success status and Google draft ID

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 404: If email not found
        HTTPException 503: If Gmail API fails or token expired
    """
    reply_service = ReplyService()
    result = await reply_service.save_draft(
        session=session,
        user=user,
        email_id=email_id,
        composed_body=request.composedBody,
        composed_subject=request.composedSubject,
    )

    if result.is_err():
        error = result.unwrap_err()
        status_code = DRAFT_ERROR_MAP.get(error, status.HTTP_500_INTERNAL_SERVER_ERROR)
        raise HTTPException(
            status_code=status_code,
            detail={"error": error.value},
        )

    draft_result = result.unwrap()
    return SaveDraftResponse(
        success=True,
        googleDraftId=draft_result.google_draft_id,
    )
