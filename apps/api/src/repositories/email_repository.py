"""Email repository for database operations.

Provides functions to:
- Check if sender is a registered contact
- Check if email already exists
- Create email records
- Get user emails
"""

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Contact, Email, User


async def is_registered_contact(
    session: AsyncSession, user_id: UUID, sender_email: str
) -> bool:
    """Check if sender is a registered contact for the user.

    Args:
        session: Database session
        user_id: The user's ID
        sender_email: The sender's email address

    Returns:
        True if sender is registered, False otherwise
    """
    contact = await get_contact_for_email(session, user_id, sender_email)
    return contact is not None


async def get_contact_for_email(
    session: AsyncSession, user_id: UUID, sender_email: str
) -> Contact | None:
    """Get contact record for a sender email.

    Args:
        session: Database session
        user_id: The user's ID
        sender_email: The sender's email address

    Returns:
        Contact if found, None otherwise
    """
    query = (
        select(Contact)
        .options(selectinload(Contact.context))
        .where(Contact.user_id == user_id, Contact.contact_email == sender_email)
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def email_exists(session: AsyncSession, google_message_id: str) -> bool:
    """Check if an email already exists in the database.

    Args:
        session: Database session
        google_message_id: The Gmail message ID

    Returns:
        True if email exists, False otherwise
    """
    query = select(Email.id).where(Email.google_message_id == google_message_id)
    result = await session.execute(query)
    return result.scalar_one_or_none() is not None


async def create_email_record(
    session: AsyncSession,
    user_id: UUID,
    contact_id: UUID | None,
    email_data: dict,
) -> Email:
    """Create a new email record in the database.

    Args:
        session: Database session
        user_id: The user's ID
        contact_id: The contact's ID (if registered)
        email_data: Parsed email data dict

    Returns:
        Created Email model instance
    """
    email = Email(
        user_id=user_id,
        contact_id=contact_id,
        google_message_id=email_data["google_message_id"],
        google_thread_id=email_data.get("thread_id"),
        sender_email=email_data["sender_email"],
        sender_name=email_data.get("sender_name"),
        subject=email_data.get("subject"),
        original_body=email_data.get("original_body"),
        received_at=email_data.get("received_at"),
        is_processed=False,
    )
    session.add(email)
    return email


async def get_user_by_firebase_uid(
    session: AsyncSession, firebase_uid: str
) -> User | None:
    """Get user by Firebase UID.

    Args:
        session: Database session
        firebase_uid: The user's Firebase UID

    Returns:
        User if found, None otherwise
    """
    query = select(User).where(User.firebase_uid == firebase_uid)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_email_by_id(session: AsyncSession, email_id: UUID) -> Email | None:
    """Get email by ID.

    Args:
        session: Database session
        email_id: The email's ID

    Returns:
        Email if found, None otherwise
    """
    query = select(Email).where(Email.id == email_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_emails_by_user_id(session: AsyncSession, user_id: UUID) -> list[Email]:
    """Get all emails for a user sorted by received_at descending.

    Args:
        session: Database session
        user_id: The user's ID

    Returns:
        List of Email objects sorted by received_at descending
    """
    query = (
        select(Email)
        .options(selectinload(Email.contact))
        .where(Email.user_id == user_id)
        .order_by(desc(Email.received_at))
    )
    result = await session.execute(query)
    return list(result.scalars().all())
