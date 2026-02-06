"""Contact management API endpoints.

Provides endpoints for:
- POST /api/contacts - Create a new contact and start learning
- GET /api/contacts - List user's contacts
- DELETE /api/contacts/{id} - Delete a contact
"""

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.middleware import get_current_user
from src.auth.schemas import FirebaseUser
from src.database import get_db
from src.repositories.contact_repository import (
    DuplicateContactError,
    create_contact,
    delete_contact,
    delete_contact_context_by_contact_id,
    get_contact_by_id,
    get_contacts_by_user_id,
    update_contact_learning_status,
)
from src.repositories.email_repository import get_user_by_firebase_uid
from src.schemas.contact import (
    ContactCreateRequest,
    ContactResponse,
    ContactsListResponse,
)
from src.services.learning_service import LearningService

router = APIRouter()


def get_contact_status(is_learning_complete: bool, learning_failed_at) -> str:
    """Determine contact learning status.

    Args:
        is_learning_complete: Whether learning is complete
        learning_failed_at: Timestamp when learning failed (or None)

    Returns:
        Status string: 'learning_started', 'learning_complete', or 'learning_failed'
    """
    if learning_failed_at is not None:
        return "learning_failed"
    if is_learning_complete:
        return "learning_complete"
    return "learning_started"


def contact_to_response(contact) -> ContactResponse:
    """Convert Contact model to ContactResponse DTO.

    Args:
        contact: Contact model instance

    Returns:
        ContactResponse DTO
    """
    return ContactResponse(
        id=str(contact.id),
        contactEmail=contact.contact_email,
        contactName=contact.contact_name,
        gmailQuery=contact.gmail_query,
        isLearningComplete=contact.is_learning_complete,
        learningFailedAt=(
            contact.learning_failed_at.isoformat()
            if contact.learning_failed_at
            else None
        ),
        createdAt=contact.created_at.isoformat(),
        status=get_contact_status(
            contact.is_learning_complete, contact.learning_failed_at
        ),
    )


@router.post(
    "/contacts", response_model=ContactResponse, status_code=status.HTTP_201_CREATED
)
async def create_contact_endpoint(
    request: ContactCreateRequest,
    background_tasks: BackgroundTasks,
    user: FirebaseUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Create a new contact and start learning process.

    Creates a new contact record with the provided email, name, and Gmail query.
    Immediately returns 201 with status "learning_started" and starts learning
    in the background.

    Args:
        request: Contact creation request body
        background_tasks: FastAPI BackgroundTasks for async processing
        user: Authenticated Firebase user
        session: Database session

    Returns:
        ContactResponse with status "learning_started"

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 409: If contact with same email already exists
    """
    # Get user from database
    db_user = await get_user_by_firebase_uid(session, user.uid)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized"},
        )

    # Create contact
    try:
        contact = await create_contact(
            session=session,
            user_id=db_user.id,
            contact_email=request.contactEmail,
            contact_name=request.contactName,
            gmail_query=request.gmailQuery,
        )
        await session.commit()
        await session.refresh(contact)
    except DuplicateContactError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "duplicate_contact"},
        ) from e

    # Start learning in background
    learning_service = LearningService()
    background_tasks.add_task(
        learning_service.process_learning,
        contact_id=contact.id,
        user_id=db_user.id,
    )

    return contact_to_response(contact)


@router.get("/contacts", response_model=ContactsListResponse)
async def get_contacts_endpoint(
    user: FirebaseUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ContactsListResponse:
    """Get all contacts for the authenticated user.

    Args:
        user: Authenticated Firebase user
        session: Database session

    Returns:
        ContactsListResponse with list of contacts and total count

    Raises:
        HTTPException 401: If not authenticated
    """
    # Get user from database
    db_user = await get_user_by_firebase_uid(session, user.uid)
    if db_user is None:
        # User not found in DB - return empty list
        return ContactsListResponse(contacts=[], total=0)

    # Get contacts
    contacts = await get_contacts_by_user_id(session, db_user.id)

    contact_responses = [contact_to_response(contact) for contact in contacts]

    return ContactsListResponse(
        contacts=contact_responses, total=len(contact_responses)
    )


@router.delete("/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact_endpoint(
    contact_id: UUID,
    user: FirebaseUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Delete a contact.

    Deletes the contact and related contact_context (via CASCADE).

    Args:
        contact_id: The contact's UUID
        user: Authenticated Firebase user
        session: Database session

    Returns:
        204 No Content on success

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If trying to delete another user's contact
        HTTPException 404: If contact not found
    """
    # Get user from database
    db_user = await get_user_by_firebase_uid(session, user.uid)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized"},
        )

    # Get contact
    contact = await get_contact_by_id(session, contact_id)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found"},
        )

    # Check ownership
    if contact.user_id != db_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden"},
        )

    # Delete contact
    await delete_contact(session, contact_id)
    await session.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/contacts/{contact_id}/retry", response_model=ContactResponse)
async def retry_learning_endpoint(
    contact_id: UUID,
    background_tasks: BackgroundTasks,
    user: FirebaseUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ContactResponse:
    """Retry learning for a failed contact.

    Resets learning status, deletes existing contact context,
    and restarts the background learning process.

    Args:
        contact_id: The contact's UUID
        background_tasks: FastAPI BackgroundTasks for async processing
        user: Authenticated Firebase user
        session: Database session

    Returns:
        ContactResponse with status "learning_started"

    Raises:
        HTTPException 401: If not authenticated
        HTTPException 403: If trying to retry another user's contact
        HTTPException 404: If contact not found
        HTTPException 409: If contact learning has not failed
    """
    db_user = await get_user_by_firebase_uid(session, user.uid)
    if db_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "unauthorized"},
        )

    contact = await get_contact_by_id(session, contact_id)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found"},
        )

    if contact.user_id != db_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "forbidden"},
        )

    if contact.learning_failed_at is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "not_failed"},
        )

    # Delete existing contact context
    await delete_contact_context_by_contact_id(session, contact_id)

    # Reset learning status
    await update_contact_learning_status(
        session=session,
        contact_id=contact_id,
        is_complete=False,
        failed_at=None,
    )
    await session.commit()
    await session.refresh(contact)

    # Start learning in background
    learning_service = LearningService()
    background_tasks.add_task(
        learning_service.process_learning,
        contact_id=contact.id,
        user_id=db_user.id,
    )

    return contact_to_response(contact)
