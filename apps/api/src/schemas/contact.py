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


class ContactInstructRequest(BaseModel):
    """Request body for POST /api/contacts/{id}/instruct endpoint.

    Attributes:
        instruction: User instruction text, non-empty, max 1000 characters
    """

    instruction: str

    @field_validator("instruction")
    @classmethod
    def validate_instruction(cls, v: str) -> str:
        """Validate instruction is non-empty and within length limit."""
        if not v or not v.strip():
            raise ValueError("Instruction cannot be empty")
        if len(v) > 1000:
            raise ValueError("Instruction must be 1000 characters or less")
        return v


class ContactsListResponse(BaseModel):
    """Response model for GET /api/contacts endpoint."""

    contacts: list[ContactResponse]
    total: int
