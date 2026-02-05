"""Tests for environment configuration."""

import os
from unittest.mock import patch


class TestSettings:
    """Settings configuration tests."""

    def test_settings_has_app_name(self) -> None:
        """Settings should have app_name attribute."""
        from src.config import Settings

        settings = Settings()
        assert hasattr(settings, "app_name")
        assert settings.app_name == "togenuki-api"

    def test_settings_has_app_version(self) -> None:
        """Settings should have app_version attribute."""
        from src.config import Settings

        settings = Settings()
        assert hasattr(settings, "app_version")
        assert settings.app_version == "0.1.0"

    def test_settings_has_debug_mode(self) -> None:
        """Settings should have debug attribute."""
        from src.config import Settings

        settings = Settings()
        assert hasattr(settings, "debug")
        assert isinstance(settings.debug, bool)

    def test_settings_debug_defaults_to_false(self) -> None:
        """Debug mode should default to False."""
        from src.config import Settings

        settings = Settings()
        assert settings.debug is False

    def test_settings_reads_from_environment(self) -> None:
        """Settings should read DEBUG from environment variables."""
        with patch.dict(os.environ, {"DEBUG": "true"}):
            from src.config import Settings

            settings = Settings()
            assert settings.debug is True

    def test_settings_has_database_url(self) -> None:
        """Settings should have database_url attribute."""
        from src.config import Settings

        settings = Settings()
        assert hasattr(settings, "database_url")

    def test_settings_database_url_has_default(self) -> None:
        """Database URL should have a default value for development."""
        from src.config import Settings

        settings = Settings()
        assert settings.database_url is not None
        assert "postgresql" in settings.database_url


class TestGetSettings:
    """get_settings function tests."""

    def test_get_settings_returns_settings_instance(self) -> None:
        """get_settings should return a Settings instance."""
        from src.config import Settings, get_settings

        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_returns_cached_instance(self) -> None:
        """get_settings should return the same cached instance."""
        from src.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2
