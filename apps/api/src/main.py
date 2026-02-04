"""FastAPI application entry point."""

from fastapi import FastAPI

from src.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
)


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
