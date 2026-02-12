"""Tests for InstructionService.

Tests for the instruction processing service that:
- Retrieves contact context from DB
- Formats user instructions via Gemini
- Appends to userInstructions array in learned_patterns
- Updates contact context in DB
- Updates learning status (started/complete/failed) during processing
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from result import Err, Ok

from src.services.gemini_service import GeminiError


def _make_mock_get_db(mock_session: MagicMock):
    """Create a mock get_db async generator that yields the given session."""

    async def mock_get_db():
        yield mock_session

    return mock_get_db


class TestProcessInstruction:
    """Tests for InstructionService.process_instruction."""

    @pytest.fixture
    def contact_id(self) -> UUID:
        return UUID("019494a5-eb1c-7000-8000-000000000002")

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create a mock ContactContext with existing learned_patterns."""
        context = MagicMock()
        context.learned_patterns = json.dumps(
            {
                "contactCharacteristics": {"tone": "formal"},
                "userReplyPatterns": {"responseStyle": "polite"},
            }
        )
        return context

    @pytest.fixture
    def mock_context_with_instructions(self) -> MagicMock:
        """Create a mock ContactContext with existing userInstructions."""
        context = MagicMock()
        context.learned_patterns = json.dumps(
            {
                "contactCharacteristics": {"tone": "formal"},
                "userReplyPatterns": {"responseStyle": "polite"},
                "userInstructions": ["既存の指示1"],
            }
        )
        return context

    @pytest.mark.asyncio
    async def test_process_instruction_appends_to_empty_instructions(
        self, contact_id: UUID, mock_context: MagicMock
    ) -> None:
        """Should add userInstructions array when it doesn't exist."""
        from src.services.instruction_service import InstructionService

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_context
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with (
            patch(
                "src.services.instruction_service.get_db",
                new=_make_mock_get_db(mock_session),
            ),
            patch(
                "src.services.instruction_service.GeminiService"
            ) as mock_gemini_cls,
            patch(
                "src.services.instruction_service.update_contact_context_patterns",
                new=AsyncMock(return_value=True),
            ) as mock_update,
        ):
            mock_gemini = MagicMock()
            mock_gemini.format_instruction = AsyncMock(
                return_value=Ok("メール末尾に「田中より」と署名を追加する")
            )
            mock_gemini_cls.return_value = mock_gemini

            service = InstructionService()
            await service.process_instruction(
                contact_id=contact_id,
                instruction="文章の最後には'田中より'と追加して",
            )

            # Verify update was called
            mock_update.assert_called_once()
            call_args = mock_update.call_args
            updated_patterns = json.loads(call_args[0][2])
            assert "userInstructions" in updated_patterns
            assert len(updated_patterns["userInstructions"]) == 1
            assert updated_patterns["userInstructions"][0] == "メール末尾に「田中より」と署名を追加する"

    @pytest.mark.asyncio
    async def test_process_instruction_appends_to_existing_instructions(
        self, contact_id: UUID, mock_context_with_instructions: MagicMock
    ) -> None:
        """Should append to existing userInstructions array."""
        from src.services.instruction_service import InstructionService

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_context_with_instructions
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with (
            patch(
                "src.services.instruction_service.get_db",
                new=_make_mock_get_db(mock_session),
            ),
            patch(
                "src.services.instruction_service.GeminiService"
            ) as mock_gemini_cls,
            patch(
                "src.services.instruction_service.update_contact_context_patterns",
                new=AsyncMock(return_value=True),
            ) as mock_update,
        ):
            mock_gemini = MagicMock()
            mock_gemini.format_instruction = AsyncMock(
                return_value=Ok("敬語は「です・ます」調に統一する")
            )
            mock_gemini_cls.return_value = mock_gemini

            service = InstructionService()
            await service.process_instruction(
                contact_id=contact_id,
                instruction="敬語はです・ます調で",
            )

            mock_update.assert_called_once()
            call_args = mock_update.call_args
            updated_patterns = json.loads(call_args[0][2])
            assert len(updated_patterns["userInstructions"]) == 2
            assert updated_patterns["userInstructions"][0] == "既存の指示1"
            assert updated_patterns["userInstructions"][1] == "敬語は「です・ます」調に統一する"

    @pytest.mark.asyncio
    async def test_process_instruction_preserves_existing_patterns(
        self, contact_id: UUID, mock_context: MagicMock
    ) -> None:
        """Should preserve contactCharacteristics and userReplyPatterns."""
        from src.services.instruction_service import InstructionService

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_context
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with (
            patch(
                "src.services.instruction_service.get_db",
                new=_make_mock_get_db(mock_session),
            ),
            patch(
                "src.services.instruction_service.GeminiService"
            ) as mock_gemini_cls,
            patch(
                "src.services.instruction_service.update_contact_context_patterns",
                new=AsyncMock(return_value=True),
            ) as mock_update,
        ):
            mock_gemini = MagicMock()
            mock_gemini.format_instruction = AsyncMock(
                return_value=Ok("整形された指示")
            )
            mock_gemini_cls.return_value = mock_gemini

            service = InstructionService()
            await service.process_instruction(
                contact_id=contact_id,
                instruction="テスト指示",
            )

            call_args = mock_update.call_args
            updated_patterns = json.loads(call_args[0][2])
            assert updated_patterns["contactCharacteristics"]["tone"] == "formal"
            assert updated_patterns["userReplyPatterns"]["responseStyle"] == "polite"

    @pytest.mark.asyncio
    async def test_process_instruction_handles_gemini_error(
        self, contact_id: UUID, mock_context: MagicMock
    ) -> None:
        """Should log error and not update DB when Gemini fails."""
        from src.services.instruction_service import InstructionService

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_context
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with (
            patch(
                "src.services.instruction_service.get_db",
                new=_make_mock_get_db(mock_session),
            ),
            patch(
                "src.services.instruction_service.GeminiService"
            ) as mock_gemini_cls,
            patch(
                "src.services.instruction_service.update_contact_context_patterns",
                new=AsyncMock(return_value=True),
            ) as mock_update,
        ):
            mock_gemini = MagicMock()
            mock_gemini.format_instruction = AsyncMock(
                return_value=Err(GeminiError.API_ERROR)
            )
            mock_gemini_cls.return_value = mock_gemini

            service = InstructionService()
            await service.process_instruction(
                contact_id=contact_id,
                instruction="テスト指示",
            )

            mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_instruction_handles_missing_context(
        self, contact_id: UUID
    ) -> None:
        """Should handle case where contact context doesn't exist."""
        from src.services.instruction_service import InstructionService

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with (
            patch(
                "src.services.instruction_service.get_db",
                new=_make_mock_get_db(mock_session),
            ),
            patch(
                "src.services.instruction_service.GeminiService"
            ) as mock_gemini_cls,
            patch(
                "src.services.instruction_service.update_contact_context_patterns",
                new=AsyncMock(return_value=True),
            ) as mock_update,
        ):
            mock_gemini = MagicMock()
            mock_gemini_cls.return_value = mock_gemini

            service = InstructionService()
            await service.process_instruction(
                contact_id=contact_id,
                instruction="テスト指示",
            )

            # Should not call Gemini or update when context missing
            mock_gemini.format_instruction.assert_not_called()
            mock_update.assert_not_called()

    @pytest.fixture
    def mock_context_with_markdown_codeblock(self) -> MagicMock:
        """Create a mock ContactContext with markdown code block wrapped JSON."""
        context = MagicMock()
        context.learned_patterns = '```json\n{"contactCharacteristics": {"tone": "formal"}, "userReplyPatterns": {"responseStyle": "polite"}}\n```'
        return context

    @pytest.mark.asyncio
    async def test_process_instruction_handles_markdown_codeblock(
        self, contact_id: UUID, mock_context_with_markdown_codeblock: MagicMock
    ) -> None:
        """Should strip markdown code block markers before parsing JSON."""
        from src.services.instruction_service import InstructionService

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_context_with_markdown_codeblock
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with (
            patch(
                "src.services.instruction_service.get_db",
                new=_make_mock_get_db(mock_session),
            ),
            patch(
                "src.services.instruction_service.GeminiService"
            ) as mock_gemini_cls,
            patch(
                "src.services.instruction_service.update_contact_context_patterns",
                new=AsyncMock(return_value=True),
            ) as mock_update,
        ):
            mock_gemini = MagicMock()
            mock_gemini.format_instruction = AsyncMock(
                return_value=Ok("メール末尾に署名を追加する")
            )
            mock_gemini_cls.return_value = mock_gemini

            service = InstructionService()
            await service.process_instruction(
                contact_id=contact_id,
                instruction="署名を追加して",
            )

            mock_update.assert_called_once()
            call_args = mock_update.call_args
            updated_patterns = json.loads(call_args[0][2])
            assert "userInstructions" in updated_patterns
            assert updated_patterns["userInstructions"][0] == "メール末尾に署名を追加する"
            assert updated_patterns["contactCharacteristics"]["tone"] == "formal"


class TestProcessInstructionLearningStatus:
    """Tests for learning status updates during instruction processing."""

    @pytest.fixture
    def contact_id(self) -> UUID:
        return UUID("019494a5-eb1c-7000-8000-000000000002")

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        context = MagicMock()
        context.learned_patterns = json.dumps(
            {
                "contactCharacteristics": {"tone": "formal"},
                "userReplyPatterns": {"responseStyle": "polite"},
            }
        )
        return context

    @pytest.mark.asyncio
    async def test_success_calls_update_learning_status_complete(
        self, contact_id: UUID, mock_context: MagicMock
    ) -> None:
        """Should call update_contact_learning_status(is_complete=True) on success."""
        from src.services.instruction_service import InstructionService

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_context
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with (
            patch(
                "src.services.instruction_service.get_db",
                new=_make_mock_get_db(mock_session),
            ),
            patch(
                "src.services.instruction_service.GeminiService"
            ) as mock_gemini_cls,
            patch(
                "src.services.instruction_service.update_contact_context_patterns",
                new=AsyncMock(return_value=True),
            ),
            patch(
                "src.services.instruction_service.update_contact_learning_status",
                new=AsyncMock(),
            ) as mock_update_status,
        ):
            mock_gemini = MagicMock()
            mock_gemini.format_instruction = AsyncMock(
                return_value=Ok("整形された指示")
            )
            mock_gemini_cls.return_value = mock_gemini

            service = InstructionService()
            await service.process_instruction(
                contact_id=contact_id,
                instruction="テスト指示",
            )

            mock_update_status.assert_called_once_with(
                mock_session, contact_id, is_complete=True
            )

    @pytest.mark.asyncio
    async def test_gemini_error_calls_update_learning_status_failed(
        self, contact_id: UUID, mock_context: MagicMock
    ) -> None:
        """Should call update_contact_learning_status with failed_at on Gemini error."""
        from src.services.instruction_service import InstructionService

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_context
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with (
            patch(
                "src.services.instruction_service.get_db",
                new=_make_mock_get_db(mock_session),
            ),
            patch(
                "src.services.instruction_service.GeminiService"
            ) as mock_gemini_cls,
            patch(
                "src.services.instruction_service.update_contact_context_patterns",
                new=AsyncMock(return_value=True),
            ) as mock_update,
            patch(
                "src.services.instruction_service.update_contact_learning_status",
                new=AsyncMock(),
            ) as mock_update_status,
        ):
            mock_gemini = MagicMock()
            mock_gemini.format_instruction = AsyncMock(
                return_value=Err(GeminiError.API_ERROR)
            )
            mock_gemini_cls.return_value = mock_gemini

            service = InstructionService()
            await service.process_instruction(
                contact_id=contact_id,
                instruction="テスト指示",
            )

            mock_update.assert_not_called()
            mock_update_status.assert_called_once()
            call_args = mock_update_status.call_args
            assert call_args[0] == (mock_session, contact_id)
            assert call_args[1]["is_complete"] is True
            assert isinstance(call_args[1]["failed_at"], datetime)

    @pytest.mark.asyncio
    async def test_json_parse_error_calls_update_learning_status_failed(
        self, contact_id: UUID
    ) -> None:
        """Should call update_contact_learning_status with failed_at on JSON parse error."""
        from src.services.instruction_service import InstructionService

        mock_context = MagicMock()
        mock_context.learned_patterns = "invalid json"

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_context
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with (
            patch(
                "src.services.instruction_service.get_db",
                new=_make_mock_get_db(mock_session),
            ),
            patch(
                "src.services.instruction_service.GeminiService"
            ) as mock_gemini_cls,
            patch(
                "src.services.instruction_service.update_contact_context_patterns",
                new=AsyncMock(return_value=True),
            ) as mock_update,
            patch(
                "src.services.instruction_service.update_contact_learning_status",
                new=AsyncMock(),
            ) as mock_update_status,
        ):
            mock_gemini = MagicMock()
            mock_gemini.format_instruction = AsyncMock(
                return_value=Ok("整形された指示")
            )
            mock_gemini_cls.return_value = mock_gemini

            service = InstructionService()
            await service.process_instruction(
                contact_id=contact_id,
                instruction="テスト指示",
            )

            mock_update.assert_not_called()
            mock_update_status.assert_called_once()
            call_args = mock_update_status.call_args
            assert call_args[0] == (mock_session, contact_id)
            assert call_args[1]["is_complete"] is True
            assert isinstance(call_args[1]["failed_at"], datetime)
