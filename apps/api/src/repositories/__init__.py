"""Repository layer for database operations."""

from src.repositories.email_repository import (
    create_email_record,
    email_exists,
    get_contact_for_email,
    is_registered_contact,
)

__all__ = [
    "create_email_record",
    "email_exists",
    "get_contact_for_email",
    "is_registered_contact",
]
