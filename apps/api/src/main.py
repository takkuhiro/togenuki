"""FastAPI application entry point."""

from fastapi import FastAPI

from src.auth.firebase_admin import initialize_firebase
from src.config import get_settings
from src.routers.contacts import router as contacts_router
from src.routers.emails import router as emails_router
from src.routers.gmail_oauth import router as gmail_oauth_router
from src.routers.gmail_watch import router as gmail_watch_router
from src.routers.reply import router as reply_router
from src.routers.webhook import router as webhook_router
from src.utils.logging import configure_logging

# Configure logging (must be called before other modules use loggers)
configure_logging()

# Initialize Firebase Admin SDK
initialize_firebase()

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)

# Include routers
app.include_router(contacts_router, prefix="/api")
app.include_router(emails_router, prefix="/api")
app.include_router(gmail_oauth_router, prefix="/api/auth/gmail")
app.include_router(reply_router, prefix="/api")
app.include_router(gmail_watch_router)
app.include_router(webhook_router)


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
