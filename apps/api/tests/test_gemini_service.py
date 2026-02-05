"""Tests for Gemini Service (Gyaru Language Conversion).

Tests for the Gemini API integration that handles:
- API client setup with google-genai SDK
- System prompt for gyaru conversion
- Sender name embedding in prompts
- Error handling and retries
"""

from unittest.mock import MagicMock, patch

import pytest


class TestGeminiService:
    """Tests for GeminiService class."""

    def test_gemini_service_initializes_with_api_key(self):
        """Test that GeminiService initializes with API key from settings."""
        from src.services.gemini_service import GeminiService

        with patch("src.services.gemini_service.get_settings") as mock_settings:
            mock_settings.return_value.gemini_api_key = "test-api-key"
            service = GeminiService()
            assert service is not None

    def test_system_prompt_contains_gyaru_rules(self):
        """Test that system prompt contains gyaru conversion rules."""
        from src.services.gemini_service import GYARU_SYSTEM_PROMPT

        # Check for key gyaru rules
        assert "ウチ" in GYARU_SYSTEM_PROMPT  # First person pronoun
        assert "先輩" in GYARU_SYSTEM_PROMPT  # How to address user
        assert "〜だし" in GYARU_SYSTEM_PROMPT or "だし" in GYARU_SYSTEM_PROMPT
        assert "草" in GYARU_SYSTEM_PROMPT or "ｗ" in GYARU_SYSTEM_PROMPT

    def test_system_prompt_includes_emoji_usage(self):
        """Test that system prompt includes emoji usage guidelines."""
        from src.services.gemini_service import GYARU_SYSTEM_PROMPT

        # Should include emoji guidelines
        emoji_count = sum(
            1 for emoji in ["💖", "✨", "🥺", "🎉", "🔥"] if emoji in GYARU_SYSTEM_PROMPT
        )
        assert emoji_count >= 3, "System prompt should include at least 3 gyaru emojis"


class TestGyaruConversion:
    """Tests for gyaru conversion functionality."""

    @pytest.mark.asyncio
    async def test_convert_to_gyaru_returns_converted_text(self):
        """Test that conversion returns transformed text."""
        from src.services.gemini_service import GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            # Mock the generate_content response
            mock_response = MagicMock()
            mock_response.text = "やっほー！先輩！💖 報告書の件だけど、明日までにお願いだし！✨"
            mock_client.models.generate_content = MagicMock(return_value=mock_response)

            service = GeminiService()
            result = await service.convert_to_gyaru(
                sender_name="上司さん", original_body="明日までに報告書を提出してください。"
            )

            assert result.is_ok()
            converted_text = result.unwrap()
            assert isinstance(converted_text, str)
            assert len(converted_text) > 0

    @pytest.mark.asyncio
    async def test_convert_to_gyaru_embeds_sender_name_in_prompt(self):
        """Test that sender name is embedded in the conversion prompt."""
        from src.services.gemini_service import GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = "変換されたテキスト"
            mock_client.models.generate_content = MagicMock(return_value=mock_response)

            service = GeminiService()
            await service.convert_to_gyaru(
                sender_name="田中課長", original_body="テスト本文"
            )

            # Verify generate_content was called with sender name context
            call_args = mock_client.models.generate_content.call_args
            contents = call_args.kwargs.get("contents") or call_args.args[1]
            assert "田中課長" in str(contents), "Sender name should be in the prompt"

    @pytest.mark.asyncio
    async def test_convert_to_gyaru_with_empty_body_returns_error(self):
        """Test that empty body returns an error."""
        from src.services.gemini_service import GeminiError, GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai"),
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            service = GeminiService()
            result = await service.convert_to_gyaru(sender_name="田中さん", original_body="")

            assert result.is_err()
            assert result.unwrap_err() == GeminiError.INVALID_INPUT


class TestGeminiErrorHandling:
    """Tests for Gemini API error handling."""

    @pytest.mark.asyncio
    async def test_api_error_returns_error_result(self):
        """Test that API errors return an error result."""
        from src.services.gemini_service import GeminiError, GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content = MagicMock(
                side_effect=Exception("API Error")
            )

            service = GeminiService()
            result = await service.convert_to_gyaru(
                sender_name="上司さん", original_body="テスト本文"
            )

            assert result.is_err()
            assert result.unwrap_err() == GeminiError.API_ERROR

    @pytest.mark.asyncio
    async def test_rate_limit_error_is_detected(self):
        """Test that rate limit errors are properly detected."""
        from src.services.gemini_service import GeminiError, GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            # Simulate rate limit error
            rate_limit_error = Exception("429 Resource has been exhausted")
            mock_client.models.generate_content = MagicMock(side_effect=rate_limit_error)

            service = GeminiService()
            result = await service.convert_to_gyaru(
                sender_name="上司さん", original_body="テスト本文"
            )

            assert result.is_err()
            assert result.unwrap_err() == GeminiError.RATE_LIMIT

    @pytest.mark.asyncio
    async def test_timeout_error_is_detected(self):
        """Test that timeout errors are properly detected."""
        import asyncio

        from src.services.gemini_service import GeminiError, GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            # Simulate timeout error
            mock_client.models.generate_content = MagicMock(
                side_effect=asyncio.TimeoutError("Request timed out")
            )

            service = GeminiService()
            result = await service.convert_to_gyaru(
                sender_name="上司さん", original_body="テスト本文"
            )

            assert result.is_err()
            assert result.unwrap_err() == GeminiError.TIMEOUT


class TestGeminiConfiguration:
    """Tests for Gemini service configuration."""

    def test_uses_gemini_25_flash_model(self):
        """Test that the service uses Gemini 2.5 Flash model."""
        from src.services.gemini_service import GEMINI_MODEL

        assert "gemini-2" in GEMINI_MODEL.lower() or "flash" in GEMINI_MODEL.lower()

    def test_model_name_is_configurable(self):
        """Test that model name can be configured via settings."""
        from src.services.gemini_service import GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai"),
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = "gemini-2.5-flash"

            service = GeminiService()
            assert service.model == "gemini-2.5-flash"
