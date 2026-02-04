"""Authentication schemas for TogeNuki."""

from enum import Enum

from pydantic import BaseModel


class AuthError(str, Enum):
    """Authentication error types."""

    INVALID_TOKEN = "invalid_token"
    EXPIRED_TOKEN = "expired_token"
    MISSING_TOKEN = "missing_token"


class FirebaseUser(BaseModel):
    """Firebase authenticated user information."""

    uid: str
    email: str
