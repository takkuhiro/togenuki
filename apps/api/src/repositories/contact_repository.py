"""Contact repository for database operations.

Provides functions to:
- Create contact (with duplicate check)
- Get contacts by user ID
- Get contact by ID
- Delete contact
- Create contact context
- Update contact learning status
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Contact, ContactContext, User


class DuplicateContactError(Exception):
    """Exception raised when trying to create a duplicate contact."""

    pass


async def create_contact(
    session: AsyncSession,
    user_id: UUID,
    contact_email: str,
    contact_name: str | None,
    gmail_query: str | None,
) -> Contact:
    """Create a new contact record.

    Args:
        session: Database session
        user_id: The user's ID
        contact_email: The contact's email address
        contact_name: The contact's name (optional)
        gmail_query: Gmail search query for this contact (optional)

    Returns:
        Created Contact instance

    Raises:
        DuplicateContactError: If contact with same user_id + contact_email exists
    """
    # Check for duplicate
    query = select(Contact).where(
        Contact.user_id == user_id, Contact.contact_email == contact_email
    )
    result = await session.execute(query)
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise DuplicateContactError(
            f"Contact with email {contact_email} already exists for this user"
        )

    contact = Contact(
        user_id=user_id,
        contact_email=contact_email,
        contact_name=contact_name,
        gmail_query=gmail_query,
        is_learning_complete=False,
    )
    session.add(contact)
    return contact


async def get_contacts_by_user_id(
    session: AsyncSession,
    user_id: UUID,
) -> list[Contact]:
    """Get all contacts for a user.

    Args:
        session: Database session
        user_id: The user's ID

    Returns:
        List of Contact instances
    """
    query = select(Contact).where(Contact.user_id == user_id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_contact_by_id(
    session: AsyncSession,
    contact_id: UUID,
) -> Contact | None:
    """Get contact by ID.

    Args:
        session: Database session
        contact_id: The contact's ID

    Returns:
        Contact if found, None otherwise
    """
    query = select(Contact).where(Contact.id == contact_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def delete_contact(
    session: AsyncSession,
    contact_id: UUID,
) -> bool:
    """Delete contact and related contact_context.

    Args:
        session: Database session
        contact_id: The contact's ID

    Returns:
        True if deleted, False if not found
    """
    contact = await get_contact_by_id(session, contact_id)
    if contact is None:
        return False

    await session.delete(contact)
    return True


async def create_contact_context(
    session: AsyncSession,
    contact_id: UUID,
    learned_patterns: str,
) -> ContactContext:
    """Create contact context with learned patterns.

    Args:
        session: Database session
        contact_id: The contact's ID
        learned_patterns: JSON string with learned patterns

    Returns:
        Created ContactContext instance
    """
    context = ContactContext(
        contact_id=contact_id,
        learned_patterns=learned_patterns,
    )
    session.add(context)
    return context


async def update_contact_learning_status(
    session: AsyncSession,
    contact_id: UUID,
    is_complete: bool,
    failed_at: datetime | None = None,
) -> None:
    """Update contact learning status.

    Args:
        session: Database session
        contact_id: The contact's ID
        is_complete: Whether learning is complete
        failed_at: Timestamp when learning failed (optional)
    """
    contact = await get_contact_by_id(session, contact_id)
    if contact is None:
        return

    contact.is_learning_complete = is_complete
    contact.learning_failed_at = failed_at


async def delete_contact_context_by_contact_id(
    session: AsyncSession,
    contact_id: UUID,
) -> None:
    """Delete contact context for a given contact.

    Args:
        session: Database session
        contact_id: The contact's ID
    """
    query = select(ContactContext).where(ContactContext.contact_id == contact_id)
    result = await session.execute(query)
    context = result.scalar_one_or_none()
    if context is not None:
        await session.delete(context)


async def update_contact_context_patterns(
    session: AsyncSession,
    contact_id: UUID,
    learned_patterns: str,
) -> bool:
    """Update learned_patterns in contact context.

    Args:
        session: Database session
        contact_id: The contact's ID
        learned_patterns: Updated JSON string with learned patterns

    Returns:
        True if updated, False if context not found
    """
    query = select(ContactContext).where(ContactContext.contact_id == contact_id)
    result = await session.execute(query)
    context = result.scalar_one_or_none()
    if context is None:
        return False

    context.learned_patterns = learned_patterns
    return True


async def get_contact_context_by_contact_id(
    session: AsyncSession,
    contact_id: UUID,
) -> ContactContext | None:
    """Get contact context by contact ID.

    Args:
        session: Database session
        contact_id: The contact's ID

    Returns:
        ContactContext if found, None otherwise
    """
    query = select(ContactContext).where(ContactContext.contact_id == contact_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_id(
    session: AsyncSession,
    user_id: UUID,
) -> User | None:
    """Get user by ID.

    Args:
        session: Database session
        user_id: The user's ID

    Returns:
        User if found, None otherwise
    """
    query = select(User).where(User.id == user_id)
    result = await session.execute(query)
    return result.scalar_one_or_none()
