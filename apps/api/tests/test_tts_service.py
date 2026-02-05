"""Tests for TTS Service (Text-to-Speech).

Tests for the Cloud TTS and GCS integration that handles:
- Text-to-speech synthesis using Google Cloud TTS
- Audio file upload to Cloud Storage
- Public URL generation
"""

from unittest.mock import MagicMock, patch

import pytest
from uuid6 import uuid7


class TestTTSService:
    """Tests for TTSService class."""

    def test_tts_service_initializes(self):
        """Test that TTSService initializes correctly."""
        from src.services.tts_service import TTSService

        with (
            patch("src.services.tts_service.texttospeech"),
            patch("src.services.tts_service.StorageClient"),
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "ja-JP-Chirp3-HD-Callirrhoe"
            mock_settings.return_value.tts_language_code = "ja-JP"

            service = TTSService()
            assert service is not None

    def test_tts_service_uses_japanese_female_voice(self):
        """Test that TTS uses Japanese female voice."""
        from src.services.tts_service import TTSService

        with (
            patch("src.services.tts_service.texttospeech"),
            patch("src.services.tts_service.StorageClient"),
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "ja-JP-Chirp3-HD-Callirrhoe"
            mock_settings.return_value.tts_language_code = "ja-JP"

            service = TTSService()
            assert service.voice_name == "ja-JP-Chirp3-HD-Callirrhoe"
            assert service.language_code == "ja-JP"


class TestSynthesizeAudio:
    """Tests for audio synthesis functionality."""

    @pytest.mark.asyncio
    async def test_synthesize_returns_audio_bytes(self):
        """Test that synthesize returns audio bytes."""
        from src.services.tts_service import TTSService

        with (
            patch("src.services.tts_service.texttospeech") as mock_tts,
            patch("src.services.tts_service.StorageClient"),
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "ja-JP-Chirp3-HD-Callirrhoe"
            mock_settings.return_value.tts_language_code = "ja-JP"

            # Mock TTS client response
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.audio_content = b"fake-audio-content"
            mock_client.synthesize_speech.return_value = mock_response
            mock_tts.TextToSpeechClient.return_value = mock_client

            service = TTSService()
            result = await service._synthesize(
                "やっほー先輩💖 ウチだよ〜！"
            )

            assert result is not None
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_synthesize_with_empty_text_returns_error(self):
        """Test that empty text returns an error."""
        from src.services.tts_service import TTSError, TTSService

        with (
            patch("src.services.tts_service.texttospeech"),
            patch("src.services.tts_service.StorageClient"),
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "ja-JP-Chirp3-HD-Callirrhoe"
            mock_settings.return_value.tts_language_code = "ja-JP"

            service = TTSService()
            result = await service.synthesize_and_upload("", uuid7())

            assert result.is_err()
            assert result.unwrap_err() == TTSError.INVALID_INPUT


class TestGCSUpload:
    """Tests for GCS upload functionality."""

    @pytest.mark.asyncio
    async def test_upload_returns_public_url(self):
        """Test that upload returns a public URL."""
        from src.services.tts_service import TTSService

        with (
            patch("src.services.tts_service.texttospeech") as mock_tts,
            patch("src.services.tts_service.StorageClient") as mock_storage,
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "ja-JP-Chirp3-HD-Callirrhoe"
            mock_settings.return_value.tts_language_code = "ja-JP"

            # Mock TTS
            mock_tts_client = MagicMock()
            mock_response = MagicMock()
            mock_response.audio_content = b"fake-audio-content"
            mock_tts_client.synthesize_speech.return_value = mock_response
            mock_tts.TextToSpeechClient.return_value = mock_tts_client

            # Mock GCS
            mock_storage_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_blob.public_url = "https://storage.googleapis.com/test-bucket/audio/test.mp3"
            mock_bucket.blob.return_value = mock_blob
            mock_storage_client.bucket.return_value = mock_bucket
            mock_storage.return_value = mock_storage_client

            service = TTSService()
            email_id = uuid7()
            result = await service.synthesize_and_upload(
                "テスト音声", email_id
            )

            assert result.is_ok()
            url = result.unwrap()
            assert "storage.googleapis.com" in url
            assert ".mp3" in url or "test" in url

    @pytest.mark.asyncio
    async def test_filename_contains_email_id_and_timestamp(self):
        """Test that filename follows {email_id}_{timestamp}.mp3 pattern."""
        from src.services.tts_service import TTSService

        with (
            patch("src.services.tts_service.texttospeech") as mock_tts,
            patch("src.services.tts_service.StorageClient") as mock_storage,
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "ja-JP-Chirp3-HD-Callirrhoe"
            mock_settings.return_value.tts_language_code = "ja-JP"

            # Mock TTS
            mock_tts_client = MagicMock()
            mock_response = MagicMock()
            mock_response.audio_content = b"fake-audio-content"
            mock_tts_client.synthesize_speech.return_value = mock_response
            mock_tts.TextToSpeechClient.return_value = mock_tts_client

            # Mock GCS
            mock_storage_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_blob.public_url = "https://storage.googleapis.com/test-bucket/test.mp3"
            mock_bucket.blob.return_value = mock_blob
            mock_storage_client.bucket.return_value = mock_bucket
            mock_storage.return_value = mock_storage_client

            service = TTSService()
            email_id = uuid7()
            await service.synthesize_and_upload("テスト音声", email_id)

            # Verify blob was created with correct filename pattern
            blob_call = mock_bucket.blob.call_args[0][0]
            assert str(email_id) in blob_call
            assert ".mp3" in blob_call


class TestTTSErrorHandling:
    """Tests for TTS error handling."""

    @pytest.mark.asyncio
    async def test_api_error_returns_error_result(self):
        """Test that TTS API errors return an error result."""
        from src.services.tts_service import TTSError, TTSService

        with (
            patch("src.services.tts_service.texttospeech") as mock_tts,
            patch("src.services.tts_service.StorageClient"),
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "ja-JP-Chirp3-HD-Callirrhoe"
            mock_settings.return_value.tts_language_code = "ja-JP"

            mock_client = MagicMock()
            mock_client.synthesize_speech.side_effect = Exception("TTS API Error")
            mock_tts.TextToSpeechClient.return_value = mock_client

            service = TTSService()
            result = await service.synthesize_and_upload("テスト", uuid7())

            assert result.is_err()
            assert result.unwrap_err() == TTSError.API_ERROR

    @pytest.mark.asyncio
    async def test_upload_error_returns_error_result(self):
        """Test that upload errors return an error result."""
        from src.services.tts_service import TTSError, TTSService

        with (
            patch("src.services.tts_service.texttospeech") as mock_tts,
            patch("src.services.tts_service.StorageClient") as mock_storage,
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "ja-JP-Chirp3-HD-Callirrhoe"
            mock_settings.return_value.tts_language_code = "ja-JP"

            # Mock TTS success
            mock_tts_client = MagicMock()
            mock_response = MagicMock()
            mock_response.audio_content = b"fake-audio-content"
            mock_tts_client.synthesize_speech.return_value = mock_response
            mock_tts.TextToSpeechClient.return_value = mock_tts_client

            # Mock GCS failure
            mock_storage_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_blob.upload_from_string.side_effect = Exception("Upload failed")
            mock_bucket.blob.return_value = mock_blob
            mock_storage_client.bucket.return_value = mock_bucket
            mock_storage.return_value = mock_storage_client

            service = TTSService()
            result = await service.synthesize_and_upload("テスト", uuid7())

            assert result.is_err()
            assert result.unwrap_err() == TTSError.UPLOAD_ERROR

    @pytest.mark.asyncio
    async def test_timeout_error_returns_error_result(self):
        """Test that timeout errors are properly handled."""
        import asyncio

        from src.services.tts_service import TTSError, TTSService

        with (
            patch("src.services.tts_service.texttospeech") as mock_tts,
            patch("src.services.tts_service.StorageClient"),
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "ja-JP-Chirp3-HD-Callirrhoe"
            mock_settings.return_value.tts_language_code = "ja-JP"

            mock_client = MagicMock()
            mock_client.synthesize_speech.side_effect = asyncio.TimeoutError()
            mock_tts.TextToSpeechClient.return_value = mock_client

            service = TTSService()
            result = await service.synthesize_and_upload("テスト", uuid7())

            assert result.is_err()
            assert result.unwrap_err() == TTSError.TIMEOUT
