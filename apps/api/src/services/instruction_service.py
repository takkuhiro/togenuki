"""Instruction Service for processing user instructions.

This service handles:
- Formatting user instructions via Gemini
- Appending formatted instructions to contact context's learned_patterns
"""

import json
import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import ContactContext
from src.repositories.contact_repository import update_contact_context_patterns
from src.services.gemini_service import GeminiService
from src.utils.logging import get_logger

logger = get_logger(__name__)


class InstructionService:
    """Service for processing user instructions for contacts."""

    async def process_instruction(
        self,
        session: AsyncSession,
        contact_id: UUID,
        instruction: str,
    ) -> None:
        """Process a user instruction and append it to contact context.

        1. Fetch contact context from DB
        2. Format instruction via Gemini
        3. Parse existing learned_patterns JSON
        4. Append formatted instruction to userInstructions array
        5. Update contact context in DB

        Args:
            session: Database session
            contact_id: The contact's ID
            instruction: Raw user instruction text
        """
        # Get contact context
        query = select(ContactContext).where(ContactContext.contact_id == contact_id)
        result = await session.execute(query)
        context = result.scalar_one_or_none()

        if context is None:
            logger.warning(f"No contact context found for contact {contact_id}")
            return

        # Format instruction via Gemini
        gemini_service = GeminiService()
        format_result = await gemini_service.format_instruction(instruction)

        if format_result.is_err():
            logger.error(
                f"Failed to format instruction for contact {contact_id}: "
                f"{format_result.unwrap_err()}"
            )
            return

        formatted_instruction = format_result.unwrap()

        # Parse existing learned_patterns and append instruction
        # Strip markdown code block markers (```json ... ```) that Gemini may add
        raw_patterns = context.learned_patterns
        stripped = re.sub(r"^```(?:json)?\s*\n?", "", raw_patterns.strip())
        stripped = re.sub(r"\n?```\s*$", "", stripped)
        try:
            patterns = json.loads(stripped)
        except (json.JSONDecodeError, TypeError):
            logger.error(
                f"Failed to parse learned_patterns for contact {contact_id}"
            )
            return

        if "userInstructions" not in patterns:
            patterns["userInstructions"] = []

        patterns["userInstructions"].append(formatted_instruction)

        # Update contact context
        updated_patterns = json.dumps(patterns, ensure_ascii=False)
        await update_contact_context_patterns(
            session, contact_id, updated_patterns
        )
        await session.commit()

        logger.info(
            f"Successfully added instruction for contact {contact_id}"
        )
