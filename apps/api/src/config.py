"""Application configuration management using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "togenuki-api"
    app_version: str = "0.1.0"
    debug: bool = False
    database_url: str = "postgresql://localhost:5432/togenuki"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
