"""Reply schemas for API requests and responses."""

from pydantic import BaseModel, ConfigDict, Field


class ComposeReplyRequest(BaseModel):
    """Request body for POST /api/emails/{email_id}/compose-reply endpoint."""

    rawText: str = Field(min_length=1)


class ComposeReplyResponse(BaseModel):
    """Response model for compose-reply endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    composedBody: str
    composedSubject: str


class SendReplyRequest(BaseModel):
    """Request body for POST /api/emails/{email_id}/send-reply endpoint."""

    composedBody: str = Field(min_length=1)
    composedSubject: str = Field(min_length=1)


class SendReplyResponse(BaseModel):
    """Response model for send-reply endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    success: bool
    googleMessageId: str


class SaveDraftRequest(BaseModel):
    """Request body for POST /api/emails/{email_id}/save-draft endpoint."""

    composedBody: str = Field(min_length=1)
    composedSubject: str = Field(min_length=1)


class SaveDraftResponse(BaseModel):
    """Response model for save-draft endpoint."""

    model_config = ConfigDict(populate_by_name=True)

    success: bool
    googleDraftId: str
