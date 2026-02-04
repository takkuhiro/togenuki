"""FastAPI application entry point."""

from fastapi import FastAPI

from src.auth.firebase_admin import initialize_firebase
from src.config import get_settings
from src.routers.gmail_oauth import router as gmail_oauth_router

# Initialize Firebase Admin SDK
initialize_firebase()

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

# Include routers
app.include_router(gmail_oauth_router, prefix="/api/auth/gmail")


@app.get("/")
async def root() -> dict:
    """Return application information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}
