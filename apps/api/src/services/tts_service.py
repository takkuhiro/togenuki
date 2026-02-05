"""TTS Service for Text-to-Speech and GCS Upload.

This service uses Google Cloud Text-to-Speech to convert text to audio
and uploads the result to Google Cloud Storage.
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from google.cloud import texttospeech
from google.cloud.storage import Client as StorageClient
from result import Err, Ok, Result

from src.config import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class TTSError(Enum):
    """Error types for TTS operations."""

    API_ERROR = "api_error"
    UPLOAD_ERROR = "upload_error"
    TIMEOUT = "timeout"
    INVALID_INPUT = "invalid_input"


class UploadError(Exception):
    """Exception raised when GCS upload fails."""

    pass


class TTSService:
    """Service for text-to-speech synthesis and GCS upload."""

    def __init__(self) -> None:
        """Initialize TTS service with settings."""
        settings = get_settings()
        self.bucket_name = settings.gcs_bucket_name
        self.voice_name = settings.tts_voice_name
        self.language_code = settings.tts_language_code
        self._tts_client: texttospeech.TextToSpeechClient | None = None
        self._storage_client: StorageClient | None = None

    @property
    def tts_client(self) -> texttospeech.TextToSpeechClient:
        """Get or create the TTS client."""
        if self._tts_client is None:
            self._tts_client = texttospeech.TextToSpeechClient()
        return self._tts_client

    @property
    def storage_client(self) -> StorageClient:
        """Get or create the storage client."""
        if self._storage_client is None:
            self._storage_client = StorageClient()
        return self._storage_client

    async def synthesize_and_upload(
        self, text: str, email_id: UUID
    ) -> Result[str, TTSError]:
        """Synthesize text to speech and upload to GCS.

        Args:
            text: Text to convert to speech
            email_id: Email ID for filename generation

        Returns:
            Result containing public URL or error
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS synthesis")
            return Err(TTSError.INVALID_INPUT)

        try:
            # 1. Synthesize audio
            audio_content = await self._synthesize(text)

            # 2. Upload to GCS
            url = await self._upload_to_gcs(audio_content, email_id)

            logger.info(f"Successfully synthesized and uploaded audio for email {email_id}")
            return Ok(url)

        except asyncio.TimeoutError:
            logger.error("TTS operation timed out")
            return Err(TTSError.TIMEOUT)
        except UploadError:
            return Err(TTSError.UPLOAD_ERROR)
        except Exception as e:
            logger.exception(f"TTS error: {e}")
            return Err(TTSError.API_ERROR)

    async def _synthesize(self, text: str) -> bytes:
        """Synthesize text to audio bytes.

        Args:
            text: Text to synthesize

        Returns:
            Audio content as bytes

        Raises:
            Exception: If synthesis fails
        """
        try:
            # Build the synthesis request
            synthesis_input = texttospeech.SynthesisInput(text=text)

            voice = texttospeech.VoiceSelectionParams(
                language_code=self.language_code,
                name=self.voice_name,
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                # speaking_rate=1.0, # Chirp3-HD-Callirrhoeの場合は不要
                # pitch=2.0,  # Chirp3-HD-Callirrhoeの場合は不要
            )

            # Call TTS API (sync call wrapped for async)
            response = await asyncio.to_thread(
                self.tts_client.synthesize_speech,
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config,
            )

            return response.audio_content

        except asyncio.TimeoutError:
            raise
        except Exception as e:
            logger.exception(f"TTS synthesis error: {e}")
            raise

    async def _upload_to_gcs(self, audio_content: bytes, email_id: UUID) -> str:
        """Upload audio content to GCS.

        Args:
            audio_content: Audio bytes to upload
            email_id: Email ID for filename

        Returns:
            Public URL of uploaded file

        Raises:
            TTSError: If upload fails
        """
        try:
            # Generate filename: {email_id}_{timestamp}.mp3
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"audio/{email_id}_{timestamp}.mp3"

            # Upload to GCS
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(filename)

            await asyncio.to_thread(
                blob.upload_from_string,
                audio_content,
                content_type="audio/mpeg",
            )

            # Return public URL
            public_url: str = blob.public_url
            logger.debug(f"Uploaded audio to {public_url}")
            return public_url

        except Exception as e:
            logger.exception(f"GCS upload error: {e}")
            raise UploadError(str(e)) from e
