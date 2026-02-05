"""Email repository for database operations.

Provides functions to:
- Check if sender is a registered contact
- Check if email already exists
- Create email records
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Contact, Email


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
    query = select(Contact).where(
        Contact.user_id == user_id, Contact.contact_email == sender_email
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
        sender_email=email_data["sender_email"],
        sender_name=email_data.get("sender_name"),
        subject=email_data.get("subject"),
        original_body=email_data.get("original_body"),
        received_at=email_data.get("received_at"),
        is_processed=False,
    )
    session.add(email)
    return email
