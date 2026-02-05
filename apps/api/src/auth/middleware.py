"""Firebase Authentication middleware for FastAPI."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth

from src.auth.schemas import AuthError, FirebaseUser

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> FirebaseUser:
    """
    Verify Firebase ID Token and return user information.

    Args:
        credentials: HTTP Bearer credentials from Authorization header.

    Returns:
        FirebaseUser with uid and email.

    Raises:
        HTTPException: 401 if token is missing, invalid, or expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": AuthError.MISSING_TOKEN.value},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": AuthError.INVALID_TOKEN.value},
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        decoded_token = auth.verify_id_token(token)
        return FirebaseUser(
            uid=decoded_token["uid"],
            email=decoded_token.get("email", ""),
        )
    except Exception as e:
        error_message = str(e).lower()
        if "expired" in error_message:
            error_type = AuthError.EXPIRED_TOKEN
        else:
            error_type = AuthError.INVALID_TOKEN

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": error_type.value},
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
