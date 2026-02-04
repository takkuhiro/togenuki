"""Tests for database session management."""

import pytest


class TestGetAsyncSessionLocal:
    """AsyncSessionLocal factory tests."""

    def test_async_session_local_exists(self) -> None:
        """AsyncSessionLocal should be importable."""
        from src.database import AsyncSessionLocal

        assert AsyncSessionLocal is not None


class TestGetDb:
    """get_db dependency function tests."""

    def test_get_db_exists(self) -> None:
        """get_db should be importable."""
        from src.database import get_db

        assert get_db is not None

    @pytest.mark.asyncio
    async def test_get_db_is_async_generator(self) -> None:
        """get_db should be an async generator."""
        import inspect

        from src.database import get_db

        assert inspect.isasyncgenfunction(get_db)


class TestAsyncEngine:
    """Async engine tests."""

    def test_async_engine_exists(self) -> None:
        """async_engine should be importable."""
        from src.database import async_engine

        assert async_engine is not None
