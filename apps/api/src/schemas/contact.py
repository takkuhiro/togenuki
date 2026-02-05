"""Contact schemas for API requests and responses."""

import re

from pydantic import BaseModel, ConfigDict, field_validator

# Simple email regex pattern
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class ContactCreateRequest(BaseModel):
    """Request body for POST /api/contacts endpoint.

    Attributes:
        contactEmail: Required, email address format
        contactName: Optional, max 255 characters
        gmailQuery: Optional, max 512 characters
    """

    contactEmail: str
    contactName: str | None = None
    gmailQuery: str | None = None

    @field_validator("contactEmail")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if not EMAIL_REGEX.match(v):
            raise ValueError("Invalid email format")
        return v


class ContactResponse(BaseModel):
    """Response model for contact data.

    Follows the design.md specification for contact endpoints.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    contactEmail: str
    contactName: str | None
    gmailQuery: str | None
    isLearningComplete: bool
    learningFailedAt: str | None
    createdAt: str
    status: str  # 'learning_started' | 'learning_complete' | 'learning_failed'


class ContactsListResponse(BaseModel):
    """Response model for GET /api/contacts endpoint."""

    contacts: list[ContactResponse]
    total: int
