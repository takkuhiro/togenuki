"""Tests for FastAPI application initialization."""

import pytest
from httpx import ASGITransport, AsyncClient


class TestHealthCheck:
    """Health check endpoint tests."""

    @pytest.mark.asyncio
    async def test_health_check_returns_200(self) -> None:
        """GET /health should return 200 OK."""
        from src.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_health_check_returns_status_ok(self) -> None:
        """GET /health should return status: ok."""
        from src.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/health")

        assert response.json() == {"status": "ok"}


class TestRootEndpoint:
    """Root endpoint tests."""

    @pytest.mark.asyncio
    async def test_root_returns_200(self) -> None:
        """GET / should return 200 OK."""
        from src.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/")

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_root_returns_app_info(self) -> None:
        """GET / should return application info."""
        from src.main import app

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/")

        data = response.json()
        assert "name" in data
        assert data["name"] == "togenuki-api"
        assert "version" in data
