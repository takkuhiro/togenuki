"""Email schemas for API responses."""

from pydantic import BaseModel, ConfigDict


class EmailDTO(BaseModel):
    """Email data transfer object for API responses.

    Follows the design.md specification for GET /api/emails response.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    senderName: str | None
    senderEmail: str
    subject: str | None
    convertedBody: str | None
    audioUrl: str | None
    isProcessed: bool
    receivedAt: str | None
    repliedAt: str | None
    replyBody: str | None
    replySubject: str | None
    replySource: str | None
    composedBody: str | None
    composedSubject: str | None
    googleDraftId: str | None


class EmailsResponse(BaseModel):
    """Response model for GET /api/emails endpoint."""

    emails: list[EmailDTO]
    total: int
