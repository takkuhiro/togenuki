"""Services package for business logic."""

# Re-export repository functions for backward compatibility
from src.repositories.email_repository import (
    create_email_record,
    email_exists,
    get_contact_for_email,
    is_registered_contact,
)
from src.services.email_processor import (
    EmailProcessorService,
    MessageResult,
    NotificationResult,
)
from src.services.gmail_service import (
    GmailApiClient,
    GmailApiError,
    extract_email_body,
    extract_sender_info,
    get_header_value,
    parse_gmail_message,
)

__all__ = [
    "EmailProcessorService",
    "GmailApiClient",
    "GmailApiError",
    "MessageResult",
    "NotificationResult",
    "create_email_record",
    "email_exists",
    "extract_email_body",
    "extract_sender_info",
    "get_contact_for_email",
    "get_header_value",
    "is_registered_contact",
    "parse_gmail_message",
]
