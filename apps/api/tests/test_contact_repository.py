"""Tests for Contact Repository.

Tests for the contact repository that handles:
- Create contact (with duplicate check)
- Get contacts by user ID
- Get contact by ID
- Delete contact (with cascade)
- Create contact context
- Update contact learning status
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from uuid6 import uuid7

from src.models import Contact, ContactContext, User


class TestCreateContact:
    """Tests for create_contact function."""

    @pytest.mark.asyncio
    async def test_create_contact_returns_contact(self) -> None:
        """create_contact should return a Contact instance."""
        from src.repositories.contact_repository import create_contact

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        user_id = uuid7()
        result = await create_contact(
            session=mock_session,
            user_id=user_id,
            contact_email="boss@example.com",
            contact_name="Boss Name",
            gmail_query="from:boss@example.com",
        )

        assert isinstance(result, Contact)
        assert result.user_id == user_id
        assert result.contact_email == "boss@example.com"
        assert result.contact_name == "Boss Name"
        assert result.gmail_query == "from:boss@example.com"
        assert result.is_learning_complete is False

    @pytest.mark.asyncio
    async def test_create_contact_with_optional_fields_none(self) -> None:
        """create_contact should work with optional fields as None."""
        from src.repositories.contact_repository import create_contact

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        user_id = uuid7()
        result = await create_contact(
            session=mock_session,
            user_id=user_id,
            contact_email="boss@example.com",
            contact_name=None,
            gmail_query=None,
        )

        assert result.contact_name is None
        assert result.gmail_query is None

    @pytest.mark.asyncio
    async def test_create_contact_adds_to_session(self) -> None:
        """create_contact should add the contact to the session."""
        from src.repositories.contact_repository import create_contact

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        user_id = uuid7()
        await create_contact(
            session=mock_session,
            user_id=user_id,
            contact_email="boss@example.com",
            contact_name=None,
            gmail_query=None,
        )

        mock_session.add.assert_called_once()
        added_contact = mock_session.add.call_args[0][0]
        assert isinstance(added_contact, Contact)

    @pytest.mark.asyncio
    async def test_create_contact_raises_on_duplicate(self) -> None:
        """create_contact should raise exception for duplicate user_id + contact_email."""
        from src.repositories.contact_repository import (
            DuplicateContactError,
            create_contact,
        )

        mock_session = AsyncMock()
        # Simulate existing contact found
        existing_contact = Contact(
            id=uuid7(),
            user_id=uuid7(),
            contact_email="boss@example.com",
        )
        mock_session.execute = AsyncMock(
            return_value=MagicMock(
                scalar_one_or_none=MagicMock(return_value=existing_contact)
            )
        )

        user_id = uuid7()
        with pytest.raises(DuplicateContactError):
            await create_contact(
                session=mock_session,
                user_id=user_id,
                contact_email="boss@example.com",
                contact_name=None,
                gmail_query=None,
            )


class TestGetContactsByUserId:
    """Tests for get_contacts_by_user_id function."""

    @pytest.mark.asyncio
    async def test_returns_list_of_contacts(self) -> None:
        """get_contacts_by_user_id should return a list of contacts."""
        from src.repositories.contact_repository import get_contacts_by_user_id

        user_id = uuid7()
        contact1 = Contact(
            id=uuid7(), user_id=user_id, contact_email="boss1@example.com"
        )
        contact2 = Contact(
            id=uuid7(), user_id=user_id, contact_email="boss2@example.com"
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [contact1, contact2]
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_contacts_by_user_id(mock_session, user_id)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(c, Contact) for c in result)

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_contacts(self) -> None:
        """get_contacts_by_user_id should return empty list when no contacts."""
        from src.repositories.contact_repository import get_contacts_by_user_id

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_contacts_by_user_id(mock_session, uuid7())

        assert result == []


class TestGetContactById:
    """Tests for get_contact_by_id function."""

    @pytest.mark.asyncio
    async def test_returns_contact_when_found(self) -> None:
        """get_contact_by_id should return contact when found."""
        from src.repositories.contact_repository import get_contact_by_id

        contact_id = uuid7()
        contact = Contact(
            id=contact_id, user_id=uuid7(), contact_email="boss@example.com"
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = contact
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_contact_by_id(mock_session, contact_id)

        assert result == contact

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        """get_contact_by_id should return None when contact not found."""
        from src.repositories.contact_repository import get_contact_by_id

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_contact_by_id(mock_session, uuid7())

        assert result is None


class TestDeleteContact:
    """Tests for delete_contact function."""

    @pytest.mark.asyncio
    async def test_returns_true_when_deleted(self) -> None:
        """delete_contact should return True when contact is deleted."""
        from src.repositories.contact_repository import delete_contact

        contact_id = uuid7()
        contact = Contact(
            id=contact_id, user_id=uuid7(), contact_email="boss@example.com"
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = contact
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await delete_contact(mock_session, contact_id)

        assert result is True
        mock_session.delete.assert_called_once_with(contact)

    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(self) -> None:
        """delete_contact should return False when contact not found."""
        from src.repositories.contact_repository import delete_contact

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await delete_contact(mock_session, uuid7())

        assert result is False
        mock_session.delete.assert_not_called()


class TestCreateContactContext:
    """Tests for create_contact_context function."""

    @pytest.mark.asyncio
    async def test_returns_contact_context(self) -> None:
        """create_contact_context should return a ContactContext instance."""
        from src.repositories.contact_repository import create_contact_context

        mock_session = AsyncMock()
        contact_id = uuid7()
        learned_patterns = '{"contactCharacteristics": {}, "userReplyPatterns": {}}'

        result = await create_contact_context(
            session=mock_session,
            contact_id=contact_id,
            learned_patterns=learned_patterns,
        )

        assert isinstance(result, ContactContext)
        assert result.contact_id == contact_id
        assert result.learned_patterns == learned_patterns

    @pytest.mark.asyncio
    async def test_adds_to_session(self) -> None:
        """create_contact_context should add to session."""
        from src.repositories.contact_repository import create_contact_context

        mock_session = AsyncMock()
        contact_id = uuid7()

        await create_contact_context(
            session=mock_session,
            contact_id=contact_id,
            learned_patterns='{"test": true}',
        )

        mock_session.add.assert_called_once()
        added_context = mock_session.add.call_args[0][0]
        assert isinstance(added_context, ContactContext)


class TestUpdateContactLearningStatus:
    """Tests for update_contact_learning_status function."""

    @pytest.mark.asyncio
    async def test_updates_is_learning_complete(self) -> None:
        """update_contact_learning_status should update is_learning_complete."""
        from src.repositories.contact_repository import update_contact_learning_status

        contact_id = uuid7()
        contact = Contact(
            id=contact_id,
            user_id=uuid7(),
            contact_email="boss@example.com",
            is_learning_complete=False,
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = contact
        mock_session.execute = AsyncMock(return_value=mock_result)

        await update_contact_learning_status(
            session=mock_session,
            contact_id=contact_id,
            is_complete=True,
        )

        assert contact.is_learning_complete is True
        assert contact.learning_failed_at is None

    @pytest.mark.asyncio
    async def test_sets_learning_failed_at(self) -> None:
        """update_contact_learning_status should set learning_failed_at on failure."""
        from src.repositories.contact_repository import update_contact_learning_status

        contact_id = uuid7()
        contact = Contact(
            id=contact_id,
            user_id=uuid7(),
            contact_email="boss@example.com",
            is_learning_complete=False,
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = contact
        mock_session.execute = AsyncMock(return_value=mock_result)

        failed_at = datetime.now(timezone.utc)
        await update_contact_learning_status(
            session=mock_session,
            contact_id=contact_id,
            is_complete=False,
            failed_at=failed_at,
        )

        assert contact.is_learning_complete is False
        assert contact.learning_failed_at == failed_at

    @pytest.mark.asyncio
    async def test_does_nothing_when_contact_not_found(self) -> None:
        """update_contact_learning_status should do nothing when contact not found."""
        from src.repositories.contact_repository import update_contact_learning_status

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Should not raise
        await update_contact_learning_status(
            session=mock_session,
            contact_id=uuid7(),
            is_complete=True,
        )


class TestGetUserById:
    """Tests for get_user_by_id function."""

    @pytest.mark.asyncio
    async def test_returns_user_when_found(self) -> None:
        """get_user_by_id should return user when found."""
        from src.repositories.contact_repository import get_user_by_id

        user_id = uuid7()
        user = User(id=user_id, firebase_uid="test-uid", email="test@example.com")

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_user_by_id(mock_session, user_id)

        assert result == user

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self) -> None:
        """get_user_by_id should return None when user not found."""
        from src.repositories.contact_repository import get_user_by_id

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await get_user_by_id(mock_session, uuid7())

        assert result is None


class TestUpdateContactContextPatterns:
    """Tests for update_contact_context_patterns function."""

    @pytest.mark.asyncio
    async def test_updates_learned_patterns_when_context_exists(self) -> None:
        """Should update learned_patterns when contact context exists."""
        import json

        from src.repositories.contact_repository import update_contact_context_patterns

        contact_id = uuid7()
        new_patterns = json.dumps(
            {
                "contactCharacteristics": {"tone": "formal"},
                "userReplyPatterns": {"responseStyle": "polite"},
                "userInstructions": ["メール末尾に「田中より」と署名を追加する"],
            }
        )

        mock_context = MagicMock()
        mock_context.learned_patterns = json.dumps(
            {
                "contactCharacteristics": {"tone": "formal"},
                "userReplyPatterns": {"responseStyle": "polite"},
            }
        )

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_context
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await update_contact_context_patterns(
            mock_session, contact_id, new_patterns
        )

        assert result is True
        assert mock_context.learned_patterns == new_patterns

    @pytest.mark.asyncio
    async def test_returns_false_when_context_not_found(self) -> None:
        """Should return False when no contact context exists."""
        from src.repositories.contact_repository import update_contact_context_patterns

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        result = await update_contact_context_patterns(
            mock_session, uuid7(), '{"userInstructions": ["test"]}'
        )

        assert result is False
