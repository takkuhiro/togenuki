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

    # Google OAuth settings
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:3000/auth/gmail/callback"

    # Firebase Admin SDK
    firebase_credentials_path: str = "secrets/firebase-service-account.json"

    # GCP Project
    project_id: str = "aitech-good-s15112"

    # Gemini API settings
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Cloud TTS settings
    tts_voice_name: str = "ja-JP-Chirp3-HD-F1"
    tts_language_code: str = "ja-JP"

    # Cloud Storage settings
    gcs_bucket_name: str = "togenuki-audio"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
