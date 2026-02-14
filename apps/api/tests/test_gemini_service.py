"""Tests for Gemini Service (Email Conversion and Pattern Analysis).

Tests for the Gemini API integration that handles:
- API client setup with google-genai SDK
- Parameterized system prompt for email conversion
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

    def test_gyaru_system_prompt_no_longer_in_gemini_service(self):
        """Test that GYARU_SYSTEM_PROMPT is no longer defined in gemini_service."""
        import src.services.gemini_service as module

        assert not hasattr(module, "GYARU_SYSTEM_PROMPT"), (
            "GYARU_SYSTEM_PROMPT should be moved to character_service"
        )


class TestEmailConversion:
    """Tests for convert_email functionality."""

    SAMPLE_SYSTEM_PROMPT = (
        "あなたはテスト用キャラクターです。メール本文を変換してください。"
    )

    @pytest.mark.asyncio
    async def test_convert_email_returns_converted_text(self):
        """Test that conversion returns transformed text."""
        from src.services.gemini_service import GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = (
                "やっほー！先輩！ 報告書の件だけど、明日までにお願いだし！"
            )
            mock_client.models.generate_content = MagicMock(return_value=mock_response)

            service = GeminiService()
            result = await service.convert_email(
                system_prompt=self.SAMPLE_SYSTEM_PROMPT,
                sender_name="上司さん",
                original_body="明日までに報告書を提出してください。",
            )

            assert result.is_ok()
            converted_text = result.unwrap()
            assert isinstance(converted_text, str)
            assert len(converted_text) > 0

    @pytest.mark.asyncio
    async def test_convert_email_uses_provided_system_prompt(self):
        """Test that convert_email uses the provided system_prompt."""
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

            custom_prompt = "あなたは冷静な執事です。メール本文を報告してください。"
            service = GeminiService()
            await service.convert_email(
                system_prompt=custom_prompt,
                sender_name="田中課長",
                original_body="テスト本文",
            )

            # Verify GenerateContentConfig was called with the custom system_prompt
            mock_genai.types.GenerateContentConfig.assert_called_once_with(
                system_instruction=custom_prompt,
                temperature=0.8,
            )

    @pytest.mark.asyncio
    async def test_convert_email_embeds_sender_name_in_prompt(self):
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
            await service.convert_email(
                system_prompt=self.SAMPLE_SYSTEM_PROMPT,
                sender_name="田中課長",
                original_body="テスト本文",
            )

            call_args = mock_client.models.generate_content.call_args
            contents = call_args.kwargs.get("contents") or call_args.args[1]
            assert "田中課長" in str(contents), "Sender name should be in the prompt"

    @pytest.mark.asyncio
    async def test_convert_email_with_empty_body_returns_error(self):
        """Test that empty body returns an error."""
        from src.services.gemini_service import GeminiError, GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai"),
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            service = GeminiService()
            result = await service.convert_email(
                system_prompt=self.SAMPLE_SYSTEM_PROMPT,
                sender_name="田中さん",
                original_body="",
            )

            assert result.is_err()
            assert result.unwrap_err() == GeminiError.INVALID_INPUT


class TestGeminiErrorHandling:
    """Tests for Gemini API error handling."""

    SAMPLE_SYSTEM_PROMPT = "テスト用プロンプト"

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
            result = await service.convert_email(
                system_prompt=self.SAMPLE_SYSTEM_PROMPT,
                sender_name="上司さん",
                original_body="テスト本文",
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
            mock_client.models.generate_content = MagicMock(
                side_effect=rate_limit_error
            )

            service = GeminiService()
            result = await service.convert_email(
                system_prompt=self.SAMPLE_SYSTEM_PROMPT,
                sender_name="上司さん",
                original_body="テスト本文",
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
            result = await service.convert_email(
                system_prompt=self.SAMPLE_SYSTEM_PROMPT,
                sender_name="上司さん",
                original_body="テスト本文",
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


class TestComposeBusinessReply:
    """Tests for compose_business_reply method."""

    @pytest.mark.asyncio
    async def test_compose_business_reply_returns_composed_text(self):
        """compose_business_reply should convert casual text to business email."""
        from src.services.gemini_service import GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = None
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = "お疲れ様です。ご連絡いただきありがとうございます。報告書の件、承知いたしました。明日中に提出いたします。"
            mock_client.models.generate_content = MagicMock(return_value=mock_response)

            service = GeminiService()
            result = await service.compose_business_reply(
                raw_text="了解っす、明日出します",
                original_email_body="明日までに報告書を提出してください。",
                sender_name="田中課長",
            )

            assert result.is_ok()
            composed = result.unwrap()
            assert isinstance(composed, str)
            assert len(composed) > 0

    @pytest.mark.asyncio
    async def test_compose_business_reply_includes_contact_context_in_prompt(self):
        """compose_business_reply should include contact_context in the prompt when provided."""
        from src.services.gemini_service import GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = None
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = "清書されたメール"
            mock_client.models.generate_content = MagicMock(return_value=mock_response)

            service = GeminiService()
            await service.compose_business_reply(
                raw_text="了解です",
                original_email_body="確認お願いします。",
                sender_name="佐藤部長",
                contact_context="丁寧で形式的なトーン。「お疲れ様です」で始めることが多い。",
            )

            call_args = mock_client.models.generate_content.call_args
            contents = call_args.kwargs.get("contents") or call_args.args[1]
            assert "丁寧で形式的なトーン" in str(contents)

    @pytest.mark.asyncio
    async def test_compose_business_reply_with_empty_text_returns_error(self):
        """compose_business_reply should return INVALID_INPUT for empty text."""
        from src.services.gemini_service import GeminiError, GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai"),
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = None

            service = GeminiService()
            result = await service.compose_business_reply(
                raw_text="",
                original_email_body="テスト本文",
                sender_name="田中さん",
            )

            assert result.is_err()
            assert result.unwrap_err() == GeminiError.INVALID_INPUT

    @pytest.mark.asyncio
    async def test_compose_business_reply_handles_api_timeout(self):
        """compose_business_reply should handle timeout errors."""
        import asyncio

        from src.services.gemini_service import GeminiError, GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = None
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content = MagicMock(
                side_effect=asyncio.TimeoutError("Request timed out")
            )

            service = GeminiService()
            result = await service.compose_business_reply(
                raw_text="了解です",
                original_email_body="テスト本文",
                sender_name="田中さん",
            )

            assert result.is_err()
            assert result.unwrap_err() == GeminiError.TIMEOUT

    @pytest.mark.asyncio
    async def test_compose_business_reply_handles_rate_limit(self):
        """compose_business_reply should detect rate limit errors."""
        from src.services.gemini_service import GeminiError, GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = None
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content = MagicMock(
                side_effect=Exception("429 Resource has been exhausted")
            )

            service = GeminiService()
            result = await service.compose_business_reply(
                raw_text="了解です",
                original_email_body="テスト本文",
                sender_name="田中さん",
            )

            assert result.is_err()
            assert result.unwrap_err() == GeminiError.RATE_LIMIT


class TestAnalyzePatterns:
    """Tests for analyze_patterns method."""

    @pytest.mark.asyncio
    async def test_analyze_patterns_returns_json_string(self):
        """analyze_patterns should return a JSON string with learned patterns."""
        from src.services.gemini_service import GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = None
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = '{"contactCharacteristics": {"tone": "formal"}, "userReplyPatterns": {"responseStyle": "polite"}}'
            mock_client.models.generate_content = MagicMock(return_value=mock_response)

            service = GeminiService()
            email_history = [
                {
                    "sender": "boss@example.com",
                    "body": "報告書を提出してください。",
                    "user_reply": "承知いたしました。",
                },
                {
                    "sender": "boss@example.com",
                    "body": "会議の件、確認お願いします。",
                    "user_reply": "はい、確認いたします。",
                },
            ]
            result = await service.analyze_patterns(
                contact_name="上司さん",
                email_history=email_history,
            )

            assert result.is_ok()
            json_str = result.unwrap()
            assert isinstance(json_str, str)
            assert "contactCharacteristics" in json_str

    @pytest.mark.asyncio
    async def test_analyze_patterns_includes_contact_name_in_prompt(self):
        """analyze_patterns should include contact name in the prompt."""
        from src.services.gemini_service import GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = None
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = (
                '{"contactCharacteristics": {}, "userReplyPatterns": {}}'
            )
            mock_client.models.generate_content = MagicMock(return_value=mock_response)

            service = GeminiService()
            email_history = [
                {
                    "sender": "boss@example.com",
                    "body": "テスト",
                    "user_reply": "テスト返信",
                },
            ]
            await service.analyze_patterns(
                contact_name="田中部長",
                email_history=email_history,
            )

            call_args = mock_client.models.generate_content.call_args
            contents = call_args.kwargs.get("contents") or call_args.args[1]
            assert "田中部長" in str(contents)

    @pytest.mark.asyncio
    async def test_analyze_patterns_with_empty_history_returns_error(self):
        """analyze_patterns should return error for empty email history."""
        from src.services.gemini_service import GeminiError, GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai"),
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = None

            service = GeminiService()
            result = await service.analyze_patterns(
                contact_name="上司さん",
                email_history=[],
            )

            assert result.is_err()
            assert result.unwrap_err() == GeminiError.INVALID_INPUT

    @pytest.mark.asyncio
    async def test_analyze_patterns_handles_api_error(self):
        """analyze_patterns should handle API errors gracefully."""
        from src.services.gemini_service import GeminiError, GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = None
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content = MagicMock(
                side_effect=Exception("API Error")
            )

            service = GeminiService()
            email_history = [
                {
                    "sender": "boss@example.com",
                    "body": "テスト",
                    "user_reply": "テスト返信",
                },
            ]
            result = await service.analyze_patterns(
                contact_name="上司さん",
                email_history=email_history,
            )

            assert result.is_err()
            assert result.unwrap_err() == GeminiError.API_ERROR

    @pytest.mark.asyncio
    async def test_analyze_patterns_handles_rate_limit(self):
        """analyze_patterns should detect rate limit errors."""
        from src.services.gemini_service import GeminiError, GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = None
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            rate_limit_error = Exception("429 Resource has been exhausted")
            mock_client.models.generate_content = MagicMock(
                side_effect=rate_limit_error
            )

            service = GeminiService()
            email_history = [
                {
                    "sender": "boss@example.com",
                    "body": "テスト",
                    "user_reply": "テスト返信",
                },
            ]
            result = await service.analyze_patterns(
                contact_name="上司さん",
                email_history=email_history,
            )

            assert result.is_err()
            assert result.unwrap_err() == GeminiError.RATE_LIMIT


class TestFormatInstruction:
    """Tests for format_instruction method."""

    @pytest.mark.asyncio
    async def test_format_instruction_returns_formatted_text(self):
        """format_instruction should return formatted instruction text."""
        from src.services.gemini_service import GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = None
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = "メール末尾に「田中より」と署名を追加する"
            mock_client.models.generate_content = MagicMock(return_value=mock_response)

            service = GeminiService()
            result = await service.format_instruction(
                "文章の最後には'田中より'と追加して"
            )

            assert result.is_ok()
            formatted = result.unwrap()
            assert isinstance(formatted, str)
            assert len(formatted) > 0

    @pytest.mark.asyncio
    async def test_format_instruction_with_empty_text_returns_error(self):
        """format_instruction should return INVALID_INPUT for empty text."""
        from src.services.gemini_service import GeminiError, GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai"),
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = None

            service = GeminiService()
            result = await service.format_instruction("")

            assert result.is_err()
            assert result.unwrap_err() == GeminiError.INVALID_INPUT

    @pytest.mark.asyncio
    async def test_format_instruction_handles_api_error(self):
        """format_instruction should handle API errors gracefully."""
        from src.services.gemini_service import GeminiError, GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = None
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client
            mock_client.models.generate_content = MagicMock(
                side_effect=Exception("API Error")
            )

            service = GeminiService()
            result = await service.format_instruction("テスト指示")

            assert result.is_err()
            assert result.unwrap_err() == GeminiError.API_ERROR

    @pytest.mark.asyncio
    async def test_format_instruction_handles_empty_response(self):
        """format_instruction should return API_ERROR when response text is None."""
        from src.services.gemini_service import GeminiError, GeminiService

        with (
            patch("src.services.gemini_service.get_settings") as mock_settings,
            patch("src.services.gemini_service.genai") as mock_genai,
        ):
            mock_settings.return_value.gemini_api_key = "test-api-key"
            mock_settings.return_value.gemini_model = None
            mock_client = MagicMock()
            mock_genai.Client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.text = None
            mock_client.models.generate_content = MagicMock(return_value=mock_response)

            service = GeminiService()
            result = await service.format_instruction("テスト指示")

            assert result.is_err()
            assert result.unwrap_err() == GeminiError.API_ERROR
