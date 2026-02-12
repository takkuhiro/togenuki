"""TTS Service for Text-to-Speech and GCS Upload.

This service uses Gemini 2.5 Flash Preview TTS to convert text to audio
and uploads the result to Google Cloud Storage.
"""

import asyncio
import io
import wave
from datetime import datetime, timezone
from enum import Enum
from uuid import UUID

from google import genai
from google.cloud.storage import Client as StorageClient
from google.genai import types
from result import Err, Ok, Result

from src.config import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

TTS_MODEL = "gemini-2.5-flash-preview-tts"


class TTSError(Enum):
    """Error types for TTS operations."""

    API_ERROR = "api_error"
    UPLOAD_ERROR = "upload_error"
    TIMEOUT = "timeout"
    INVALID_INPUT = "invalid_input"


class UploadError(Exception):
    """Exception raised when GCS upload fails."""

    pass


def _pcm_to_wav(
    pcm_data: bytes,
    channels: int = 1,
    rate: int = 24000,
    sample_width: int = 2,
) -> bytes:
    """Convert raw PCM data to WAV format."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


class TTSService:
    """Service for text-to-speech synthesis and GCS upload."""

    def __init__(self) -> None:
        """Initialize TTS service with settings."""
        settings = get_settings()
        self.bucket_name = settings.gcs_bucket_name
        self.voice_name = settings.tts_voice_name
        self.api_key = settings.gemini_api_key
        self._genai_client: genai.Client | None = None
        self._storage_client: StorageClient | None = None

    @property
    def genai_client(self) -> genai.Client:
        """Get or create the Gemini client."""
        if self._genai_client is None:
            self._genai_client = genai.Client(api_key=self.api_key)
        return self._genai_client

    @property
    def storage_client(self) -> StorageClient:
        """Get or create the storage client."""
        if self._storage_client is None:
            self._storage_client = StorageClient()
        return self._storage_client

    async def synthesize_and_upload(
        self,
        text: str,
        email_id: UUID,
        voice_name: str | None = None,
    ) -> Result[str, TTSError]:
        """Synthesize text to speech and upload to GCS.

        Args:
            text: Text to convert to speech
            email_id: Email ID for filename generation
            voice_name: Optional voice name override. Falls back to settings if None.

        Returns:
            Result containing public URL or error
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS synthesis")
            return Err(TTSError.INVALID_INPUT)

        try:
            # 1. Synthesize audio
            audio_content = await self._synthesize(text, voice_name=voice_name)

            # 2. Upload to GCS
            url = await self._upload_to_gcs(audio_content, email_id)

            logger.info(
                f"Successfully synthesized and uploaded audio for email {email_id}"
            )
            return Ok(url)

        except asyncio.TimeoutError:
            logger.error("TTS operation timed out")
            return Err(TTSError.TIMEOUT)
        except UploadError:
            return Err(TTSError.UPLOAD_ERROR)
        except Exception as e:
            logger.exception(f"TTS error: {e}")
            return Err(TTSError.API_ERROR)

    async def _synthesize(self, text: str, voice_name: str | None = None) -> bytes:
        """Synthesize text to audio bytes using Gemini TTS.

        Args:
            text: Text to synthesize
            voice_name: Optional voice name override. Falls back to settings if None.

        Returns:
            Audio content as WAV bytes

        Raises:
            Exception: If synthesis fails
        """
        try:
            effective_voice_name = voice_name or self.voice_name

            response = await asyncio.to_thread(
                self.genai_client.models.generate_content,
                model=TTS_MODEL,
                contents=text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=effective_voice_name,
                            )
                        )
                    ),
                ),
            )

            pcm_data = response.candidates[0].content.parts[0].inline_data.data
            return _pcm_to_wav(pcm_data)

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
            UploadError: If upload fails
        """
        try:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"audio/{email_id}_{timestamp}.wav"

            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(filename)

            await asyncio.to_thread(
                blob.upload_from_string,
                audio_content,
                content_type="audio/wav",
            )

            public_url: str = blob.public_url
            logger.debug(f"Uploaded audio to {public_url}")
            return public_url

        except Exception as e:
            logger.exception(f"GCS upload error: {e}")
            raise UploadError(str(e)) from e
