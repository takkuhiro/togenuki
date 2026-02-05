"""Gemini Service for Gyaru Language Conversion.

This service uses Gemini 2.5 Flash to convert email text into
"全肯定ギャル" (all-affirming gyaru) style speech.
"""

import asyncio
from enum import Enum

from google import genai
from result import Err, Ok, Result

from src.config import get_settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

# Default model name
GEMINI_MODEL = "gemini-2.5-flash"

# System prompt for gyaru conversion
GYARU_SYSTEM_PROMPT = """あなたは「全肯定ギャル」として、メールの内容を親しみやすく変換する役割を担います。

## 変換ルール

1. **一人称**: 「ウチ」を使用
2. **相手の呼び方**: 送信者は「〇〇さん」（送信者名を使用）、メールを受け取るユーザーは「先輩」と呼ぶ
3. **語尾のバリエーション**:
   - 「〜だし！」
   - 「〜じゃね？」
   - 「〜なんだけどｗ」
   - 「草」
   - 「マジ」「ガチ」
   - 「〜っしょ！」
4. **ポジティブ解釈**: 怒られている内容でも「先輩のこと思ってくれてるんだ！」のようにポジティブに解釈
5. **絵文字の使用**: 適度に絵文字を使用する（💖, ✨, 🥺, 🎉, 🔥）
6. **内容の正確性**: 元のメールの重要な情報（日付、金額、依頼事項）は正確に伝える

## 変換例

**元のメール**: 「明日までに報告書を提出してください。遅れは認められません。」

**変換後**: 「やっほー先輩💖 〇〇さんからメール来てるし！報告書、明日までにお願いだって✨ ちょっと急ぎっぽいけど、先輩ならできるっしょ！🔥 ウチも応援してるから頑張ってね〜！」

## 出力形式

変換後のテキストのみを出力してください。説明や前置きは不要です。
"""


class GeminiError(Enum):
    """Error types for Gemini API."""

    RATE_LIMIT = "rate_limit"
    API_ERROR = "api_error"
    TIMEOUT = "timeout"
    INVALID_INPUT = "invalid_input"


class GeminiService:
    """Service for converting email text to gyaru style using Gemini."""

    def __init__(self) -> None:
        """Initialize the Gemini service with API key from settings."""
        settings = get_settings()
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model or GEMINI_MODEL
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        """Get or create the Gemini client."""
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    async def convert_to_gyaru(
        self, sender_name: str, original_body: str
    ) -> Result[str, GeminiError]:
        """Convert email body to gyaru style.

        Args:
            sender_name: Name of the email sender (e.g., "田中課長")
            original_body: Original email body text

        Returns:
            Result containing converted text or error
        """
        if not original_body or not original_body.strip():
            logger.warning("Empty body provided for gyaru conversion")
            return Err(GeminiError.INVALID_INPUT)

        try:
            # Build the user prompt with sender context
            user_prompt = f"""送信者: {sender_name}

以下のメール本文をギャル語に変換してください:

{original_body}"""

            # Call Gemini API (sync call wrapped for async compatibility)
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model,
                contents=user_prompt,
                config=genai.types.GenerateContentConfig(
                    system_instruction=GYARU_SYSTEM_PROMPT,
                    temperature=0.8,
                    max_output_tokens=1024,
                ),
            )

            converted_text = response.text
            if converted_text is None:
                logger.error("Gemini returned empty response")
                return Err(GeminiError.API_ERROR)
            logger.info(
                f"Successfully converted email from {sender_name} to gyaru style"
            )
            return Ok(converted_text)

        except asyncio.TimeoutError:
            logger.error("Gemini API request timed out")
            return Err(GeminiError.TIMEOUT)
        except Exception as e:
            error_str = str(e).lower()
            if "429" in error_str or "exhausted" in error_str or "rate" in error_str:
                logger.warning(f"Gemini API rate limited: {e}")
                return Err(GeminiError.RATE_LIMIT)
            logger.exception(f"Gemini API error: {e}")
            return Err(GeminiError.API_ERROR)
