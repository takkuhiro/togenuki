"""Tests for TTS Service (Text-to-Speech).

Tests for the Gemini TTS and GCS integration that handles:
- Text-to-speech synthesis using Gemini 2.5 Flash Preview TTS
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
            patch("src.services.tts_service.StorageClient"),
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "Callirrhoe"
            mock_settings.return_value.gemini_api_key = "test-key"

            service = TTSService()
            assert service is not None

    def test_tts_service_uses_configured_voice(self):
        """Test that TTS uses the configured voice name."""
        from src.services.tts_service import TTSService

        with (
            patch("src.services.tts_service.StorageClient"),
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "Callirrhoe"
            mock_settings.return_value.gemini_api_key = "test-key"

            service = TTSService()
            assert service.voice_name == "Callirrhoe"


class TestSynthesizeAudio:
    """Tests for audio synthesis functionality."""

    @pytest.mark.asyncio
    async def test_synthesize_returns_audio_bytes(self):
        """Test that synthesize returns audio bytes (WAV format)."""
        from src.services.tts_service import TTSService

        with (
            patch("src.services.tts_service.genai") as mock_genai,
            patch("src.services.tts_service.StorageClient"),
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "Callirrhoe"
            mock_settings.return_value.gemini_api_key = "test-key"

            # Mock Gemini TTS response
            mock_client = MagicMock()
            mock_inline_data = MagicMock()
            mock_inline_data.data = b"\x00" * 4800  # fake PCM data
            mock_part = MagicMock()
            mock_part.inline_data = mock_inline_data
            mock_content = MagicMock()
            mock_content.parts = [mock_part]
            mock_candidate = MagicMock()
            mock_candidate.content = mock_content
            mock_response = MagicMock()
            mock_response.candidates = [mock_candidate]
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            service = TTSService()
            result = await service._synthesize("やっほー先輩！ ウチだよ〜！")

            assert result is not None
            assert len(result) > 0
            # WAV files start with "RIFF" header
            assert result[:4] == b"RIFF"

    @pytest.mark.asyncio
    async def test_synthesize_with_empty_text_returns_error(self):
        """Test that empty text returns an error."""
        from src.services.tts_service import TTSError, TTSService

        with (
            patch("src.services.tts_service.genai"),
            patch("src.services.tts_service.StorageClient"),
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "Callirrhoe"
            mock_settings.return_value.gemini_api_key = "test-key"

            service = TTSService()
            result = await service.synthesize_and_upload("", uuid7())

            assert result.is_err()
            assert result.unwrap_err() == TTSError.INVALID_INPUT

    @pytest.mark.asyncio
    async def test_synthesize_calls_gemini_with_correct_config(self):
        """Test that synthesize calls Gemini TTS with correct voice config."""
        from src.services.tts_service import TTS_MODEL, TTSService

        with (
            patch("src.services.tts_service.genai") as mock_genai,
            patch("src.services.tts_service.types") as mock_types,
            patch("src.services.tts_service.StorageClient"),
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "Callirrhoe"
            mock_settings.return_value.gemini_api_key = "test-key"

            # Mock Gemini TTS response
            mock_client = MagicMock()
            mock_inline_data = MagicMock()
            mock_inline_data.data = b"\x00" * 4800
            mock_part = MagicMock()
            mock_part.inline_data = mock_inline_data
            mock_content = MagicMock()
            mock_content.parts = [mock_part]
            mock_candidate = MagicMock()
            mock_candidate.content = mock_content
            mock_response = MagicMock()
            mock_response.candidates = [mock_candidate]
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            service = TTSService()
            await service._synthesize("テスト音声")

            # Verify generate_content was called with TTS model
            mock_client.models.generate_content.assert_called_once()
            call_kwargs = mock_client.models.generate_content.call_args
            assert call_kwargs.kwargs["model"] == TTS_MODEL

            # Verify voice config was constructed
            mock_types.PrebuiltVoiceConfig.assert_called_once_with(
                voice_name="Callirrhoe",
            )


class TestGCSUpload:
    """Tests for GCS upload functionality."""

    @pytest.mark.asyncio
    async def test_upload_returns_public_url(self):
        """Test that upload returns a public URL."""
        from src.services.tts_service import TTSService

        with (
            patch("src.services.tts_service.genai") as mock_genai,
            patch("src.services.tts_service.StorageClient") as mock_storage,
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "Callirrhoe"
            mock_settings.return_value.gemini_api_key = "test-key"

            # Mock Gemini TTS
            mock_client = MagicMock()
            mock_inline_data = MagicMock()
            mock_inline_data.data = b"\x00" * 4800
            mock_part = MagicMock()
            mock_part.inline_data = mock_inline_data
            mock_content = MagicMock()
            mock_content.parts = [mock_part]
            mock_candidate = MagicMock()
            mock_candidate.content = mock_content
            mock_response = MagicMock()
            mock_response.candidates = [mock_candidate]
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            # Mock GCS
            mock_storage_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_blob.public_url = (
                "https://storage.googleapis.com/test-bucket/audio/test.wav"
            )
            mock_bucket.blob.return_value = mock_blob
            mock_storage_client.bucket.return_value = mock_bucket
            mock_storage.return_value = mock_storage_client

            service = TTSService()
            email_id = uuid7()
            result = await service.synthesize_and_upload("テスト音声", email_id)

            assert result.is_ok()
            url = result.unwrap()
            assert "storage.googleapis.com" in url

    @pytest.mark.asyncio
    async def test_filename_contains_email_id_and_timestamp(self):
        """Test that filename follows {email_id}_{timestamp}.wav pattern."""
        from src.services.tts_service import TTSService

        with (
            patch("src.services.tts_service.genai") as mock_genai,
            patch("src.services.tts_service.StorageClient") as mock_storage,
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "Callirrhoe"
            mock_settings.return_value.gemini_api_key = "test-key"

            # Mock Gemini TTS
            mock_client = MagicMock()
            mock_inline_data = MagicMock()
            mock_inline_data.data = b"\x00" * 4800
            mock_part = MagicMock()
            mock_part.inline_data = mock_inline_data
            mock_content = MagicMock()
            mock_content.parts = [mock_part]
            mock_candidate = MagicMock()
            mock_candidate.content = mock_content
            mock_response = MagicMock()
            mock_response.candidates = [mock_candidate]
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            # Mock GCS
            mock_storage_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_blob.public_url = "https://storage.googleapis.com/test-bucket/test.wav"
            mock_bucket.blob.return_value = mock_blob
            mock_storage_client.bucket.return_value = mock_bucket
            mock_storage.return_value = mock_storage_client

            service = TTSService()
            email_id = uuid7()
            await service.synthesize_and_upload("テスト音声", email_id)

            # Verify blob was created with correct filename pattern
            blob_call = mock_bucket.blob.call_args[0][0]
            assert str(email_id) in blob_call
            assert ".wav" in blob_call


class TestVoiceNameParameter:
    """Tests for voice_name parameter in synthesize_and_upload."""

    @pytest.mark.asyncio
    async def test_custom_voice_name_is_used_in_synthesis(self):
        """Test that a custom voice_name overrides the default."""
        from src.services.tts_service import TTSService

        with (
            patch("src.services.tts_service.genai") as mock_genai,
            patch("src.services.tts_service.types") as mock_types,
            patch("src.services.tts_service.StorageClient") as mock_storage,
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "Callirrhoe"
            mock_settings.return_value.gemini_api_key = "test-key"

            # Mock Gemini TTS
            mock_client = MagicMock()
            mock_inline_data = MagicMock()
            mock_inline_data.data = b"\x00" * 4800
            mock_part = MagicMock()
            mock_part.inline_data = mock_inline_data
            mock_content = MagicMock()
            mock_content.parts = [mock_part]
            mock_candidate = MagicMock()
            mock_candidate.content = mock_content
            mock_response = MagicMock()
            mock_response.candidates = [mock_candidate]
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            # Mock GCS
            mock_storage_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_blob.public_url = "https://storage.googleapis.com/test-bucket/test.wav"
            mock_bucket.blob.return_value = mock_blob
            mock_storage_client.bucket.return_value = mock_bucket
            mock_storage.return_value = mock_storage_client

            service = TTSService()
            custom_voice = "Zubenelgenubi"
            result = await service.synthesize_and_upload(
                "テスト音声", uuid7(), voice_name=custom_voice
            )

            assert result.is_ok()
            # Verify PrebuiltVoiceConfig was called with the custom voice
            mock_types.PrebuiltVoiceConfig.assert_called_once_with(
                voice_name=custom_voice,
            )

    @pytest.mark.asyncio
    async def test_none_voice_name_falls_back_to_settings(self):
        """Test that None voice_name uses the settings default."""
        from src.services.tts_service import TTSService

        with (
            patch("src.services.tts_service.genai") as mock_genai,
            patch("src.services.tts_service.types") as mock_types,
            patch("src.services.tts_service.StorageClient") as mock_storage,
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "Callirrhoe"
            mock_settings.return_value.gemini_api_key = "test-key"

            # Mock Gemini TTS
            mock_client = MagicMock()
            mock_inline_data = MagicMock()
            mock_inline_data.data = b"\x00" * 4800
            mock_part = MagicMock()
            mock_part.inline_data = mock_inline_data
            mock_content = MagicMock()
            mock_content.parts = [mock_part]
            mock_candidate = MagicMock()
            mock_candidate.content = mock_content
            mock_response = MagicMock()
            mock_response.candidates = [mock_candidate]
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

            # Mock GCS
            mock_storage_client = MagicMock()
            mock_bucket = MagicMock()
            mock_blob = MagicMock()
            mock_blob.public_url = "https://storage.googleapis.com/test-bucket/test.wav"
            mock_bucket.blob.return_value = mock_blob
            mock_storage_client.bucket.return_value = mock_bucket
            mock_storage.return_value = mock_storage_client

            service = TTSService()
            result = await service.synthesize_and_upload(
                "テスト音声", uuid7(), voice_name=None
            )

            assert result.is_ok()
            # Verify PrebuiltVoiceConfig was called with default settings voice
            mock_types.PrebuiltVoiceConfig.assert_called_once_with(
                voice_name="Callirrhoe",
            )


class TestTTSErrorHandling:
    """Tests for TTS error handling."""

    @pytest.mark.asyncio
    async def test_api_error_returns_error_result(self):
        """Test that TTS API errors return an error result."""
        from src.services.tts_service import TTSError, TTSService

        with (
            patch("src.services.tts_service.genai") as mock_genai,
            patch("src.services.tts_service.StorageClient"),
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "Callirrhoe"
            mock_settings.return_value.gemini_api_key = "test-key"

            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = Exception(
                "TTS API Error"
            )
            mock_genai.Client.return_value = mock_client

            service = TTSService()
            result = await service.synthesize_and_upload("テスト", uuid7())

            assert result.is_err()
            assert result.unwrap_err() == TTSError.API_ERROR

    @pytest.mark.asyncio
    async def test_upload_error_returns_error_result(self):
        """Test that upload errors return an error result."""
        from src.services.tts_service import TTSError, TTSService

        with (
            patch("src.services.tts_service.genai") as mock_genai,
            patch("src.services.tts_service.StorageClient") as mock_storage,
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "Callirrhoe"
            mock_settings.return_value.gemini_api_key = "test-key"

            # Mock Gemini TTS success
            mock_client = MagicMock()
            mock_inline_data = MagicMock()
            mock_inline_data.data = b"\x00" * 4800
            mock_part = MagicMock()
            mock_part.inline_data = mock_inline_data
            mock_content = MagicMock()
            mock_content.parts = [mock_part]
            mock_candidate = MagicMock()
            mock_candidate.content = mock_content
            mock_response = MagicMock()
            mock_response.candidates = [mock_candidate]
            mock_client.models.generate_content.return_value = mock_response
            mock_genai.Client.return_value = mock_client

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
            patch("src.services.tts_service.genai") as mock_genai,
            patch("src.services.tts_service.StorageClient"),
            patch("src.services.tts_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.gcs_bucket_name = "test-bucket"
            mock_settings.return_value.tts_voice_name = "Callirrhoe"
            mock_settings.return_value.gemini_api_key = "test-key"

            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = asyncio.TimeoutError()
            mock_genai.Client.return_value = mock_client

            service = TTSService()
            result = await service.synthesize_and_upload("テスト", uuid7())

            assert result.is_err()
            assert result.unwrap_err() == TTSError.TIMEOUT


class TestPcmToWav:
    """Tests for PCM to WAV conversion."""

    def test_pcm_to_wav_produces_valid_wav(self):
        """Test that _pcm_to_wav produces valid WAV data."""
        from src.services.tts_service import _pcm_to_wav

        pcm_data = b"\x00" * 4800  # 0.1 seconds of silence at 24kHz
        wav_data = _pcm_to_wav(pcm_data)

        # WAV files start with "RIFF" header
        assert wav_data[:4] == b"RIFF"
        # WAV files contain "WAVE" format identifier
        assert wav_data[8:12] == b"WAVE"
        # WAV data should be larger than PCM (includes headers)
        assert len(wav_data) > len(pcm_data)
