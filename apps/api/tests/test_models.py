"""Tests for SQLAlchemy ORM models."""

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from uuid6 import uuid7


class TestUserModel:
    """User model tests."""

    def test_user_model_exists(self) -> None:
        """User model should be importable."""
        from src.models import User

        assert User is not None

    def test_user_has_required_fields(self) -> None:
        """User model should have all required fields."""
        from src.models import User

        assert hasattr(User, "id")
        assert hasattr(User, "firebase_uid")
        assert hasattr(User, "email")
        assert hasattr(User, "gmail_refresh_token")
        assert hasattr(User, "gmail_access_token")
        assert hasattr(User, "gmail_token_expires_at")
        assert hasattr(User, "created_at")

    def test_user_table_name(self) -> None:
        """User model should have correct table name."""
        from src.models import User

        assert User.__tablename__ == "users"

    def test_user_can_be_created(self) -> None:
        """User instance should be creatable with required fields."""
        from src.models import User

        user = User(
            firebase_uid="test-uid-123",
            email="test@example.com",
        )
        assert user.firebase_uid == "test-uid-123"
        assert user.email == "test@example.com"

    def test_user_oauth_fields_are_optional(self) -> None:
        """OAuth fields should be optional (nullable)."""
        from src.models import User

        user = User(
            firebase_uid="test-uid-123",
            email="test@example.com",
        )
        assert user.gmail_refresh_token is None
        assert user.gmail_access_token is None
        assert user.gmail_token_expires_at is None

    def test_user_has_selected_character_id_field(self) -> None:
        """User model should have selected_character_id field."""
        from src.models import User

        assert hasattr(User, "selected_character_id")

    def test_user_selected_character_id_defaults_to_none(self) -> None:
        """selected_character_id should default to None (nullable)."""
        from src.models import User

        user = User(
            firebase_uid="test-uid-123",
            email="test@example.com",
        )
        assert user.selected_character_id is None

    def test_user_selected_character_id_can_be_set(self) -> None:
        """selected_character_id should be settable."""
        from src.models import User

        user = User(
            firebase_uid="test-uid-123",
            email="test@example.com",
            selected_character_id="butler",
        )
        assert user.selected_character_id == "butler"


class TestContactModel:
    """Contact model tests."""

    def test_contact_model_exists(self) -> None:
        """Contact model should be importable."""
        from src.models import Contact

        assert Contact is not None

    def test_contact_has_required_fields(self) -> None:
        """Contact model should have all required fields."""
        from src.models import Contact

        assert hasattr(Contact, "id")
        assert hasattr(Contact, "user_id")
        assert hasattr(Contact, "contact_email")
        assert hasattr(Contact, "contact_name")
        assert hasattr(Contact, "gmail_query")
        assert hasattr(Contact, "is_learning_complete")
        assert hasattr(Contact, "learning_failed_at")
        assert hasattr(Contact, "created_at")

    def test_contact_table_name(self) -> None:
        """Contact model should have correct table name."""
        from src.models import Contact

        assert Contact.__tablename__ == "contacts"

    def test_contact_can_be_created(self) -> None:
        """Contact instance should be creatable with required fields."""
        from src.models import Contact

        test_user_id = uuid7()
        contact = Contact(
            user_id=test_user_id,
            contact_email="boss@example.com",
            contact_name="Boss Name",
        )
        assert contact.user_id == test_user_id
        assert contact.contact_email == "boss@example.com"
        assert contact.contact_name == "Boss Name"

    def test_contact_is_learning_complete_field_exists(self) -> None:
        """is_learning_complete field should exist."""
        from src.models import Contact

        contact = Contact(
            user_id=uuid7(),
            contact_email="boss@example.com",
        )
        # Default value is applied when inserted to DB, not on instance creation
        assert hasattr(contact, "is_learning_complete")


class TestEmailModel:
    """Email model tests."""

    def test_email_model_exists(self) -> None:
        """Email model should be importable."""
        from src.models import Email

        assert Email is not None

    def test_email_has_required_fields(self) -> None:
        """Email model should have all required fields."""
        from src.models import Email

        assert hasattr(Email, "id")
        assert hasattr(Email, "user_id")
        assert hasattr(Email, "contact_id")
        assert hasattr(Email, "google_message_id")
        assert hasattr(Email, "sender_email")
        assert hasattr(Email, "sender_name")
        assert hasattr(Email, "subject")
        assert hasattr(Email, "original_body")
        assert hasattr(Email, "converted_body")
        assert hasattr(Email, "audio_url")
        assert hasattr(Email, "received_at")
        assert hasattr(Email, "is_processed")
        assert hasattr(Email, "created_at")

    def test_email_has_reply_fields(self) -> None:
        """Email model should have reply-related fields."""
        from src.models import Email

        assert hasattr(Email, "reply_body")
        assert hasattr(Email, "reply_subject")
        assert hasattr(Email, "replied_at")
        assert hasattr(Email, "reply_google_message_id")

    def test_email_table_name(self) -> None:
        """Email model should have correct table name."""
        from src.models import Email

        assert Email.__tablename__ == "emails"

    def test_email_can_be_created(self) -> None:
        """Email instance should be creatable with required fields."""
        from src.models import Email

        test_user_id = uuid7()
        email = Email(
            user_id=test_user_id,
            google_message_id="msg-123",
            sender_email="boss@example.com",
            sender_name="Boss",
            subject="Important",
            original_body="Please do this.",
        )
        assert email.user_id == test_user_id
        assert email.google_message_id == "msg-123"
        assert email.sender_email == "boss@example.com"

    def test_email_reply_fields_are_optional(self) -> None:
        """Reply fields should be optional (nullable) by default."""
        from src.models import Email

        email = Email(
            user_id=uuid7(),
            google_message_id="msg-123",
            sender_email="boss@example.com",
        )
        assert email.reply_body is None
        assert email.reply_subject is None
        assert email.replied_at is None
        assert email.reply_google_message_id is None

    def test_email_is_processed_field_exists(self) -> None:
        """is_processed field should exist."""
        from src.models import Email

        email = Email(
            user_id=uuid7(),
            google_message_id="msg-123",
            sender_email="boss@example.com",
        )
        # Default value is applied when inserted to DB, not on instance creation
        assert hasattr(email, "is_processed")


class TestContactContextModel:
    """ContactContext model tests."""

    def test_contact_context_model_exists(self) -> None:
        """ContactContext model should be importable."""
        from src.models import ContactContext

        assert ContactContext is not None

    def test_contact_context_has_required_fields(self) -> None:
        """ContactContext model should have all required fields."""
        from src.models import ContactContext

        assert hasattr(ContactContext, "id")
        assert hasattr(ContactContext, "contact_id")
        assert hasattr(ContactContext, "learned_patterns")
        assert hasattr(ContactContext, "updated_at")

    def test_contact_context_table_name(self) -> None:
        """ContactContext model should have correct table name."""
        from src.models import ContactContext

        assert ContactContext.__tablename__ == "contact_context"

    def test_contact_context_can_be_created(self) -> None:
        """ContactContext instance should be creatable with required fields."""
        from src.models import ContactContext

        test_contact_id = uuid7()
        learned_patterns = '{"contactCharacteristics": {}, "userReplyPatterns": {}}'
        context = ContactContext(
            contact_id=test_contact_id,
            learned_patterns=learned_patterns,
        )
        assert context.contact_id == test_contact_id
        assert context.learned_patterns == learned_patterns


class TestBase:
    """Base model tests."""

    def test_base_exists(self) -> None:
        """Base should be importable."""
        from src.models import Base

        assert Base is not None


class TestDatabaseIntegration:
    """Database integration tests using SQLite in-memory."""

    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite engine for testing."""
        from src.models import Base

        engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(engine)
        return engine

    @pytest.fixture
    def session(self, engine):
        """Create database session."""
        with Session(engine) as session:
            yield session

    def test_can_create_user_in_database(self, session: Session) -> None:
        """Should be able to create a user in the database."""
        from src.models import User

        user = User(
            firebase_uid="uid-123",
            email="test@example.com",
        )
        session.add(user)
        session.commit()

        result = session.execute(select(User)).scalar_one()
        assert result.firebase_uid == "uid-123"
        assert result.email == "test@example.com"
        assert result.id is not None

    def test_can_create_contact_with_user(self, session: Session) -> None:
        """Should be able to create a contact linked to a user."""
        from src.models import Contact, User

        user = User(firebase_uid="uid-123", email="test@example.com")
        session.add(user)
        session.commit()

        contact = Contact(
            user_id=user.id,
            contact_email="boss@example.com",
            contact_name="Boss",
        )
        session.add(contact)
        session.commit()

        result = session.execute(select(Contact)).scalar_one()
        assert result.user_id == user.id
        assert result.contact_email == "boss@example.com"

    def test_can_create_email_with_user(self, session: Session) -> None:
        """Should be able to create an email linked to a user."""
        from src.models import Email, User

        user = User(firebase_uid="uid-123", email="test@example.com")
        session.add(user)
        session.commit()

        email = Email(
            user_id=user.id,
            google_message_id="msg-123",
            sender_email="boss@example.com",
            sender_name="Boss",
            subject="Test Subject",
            original_body="Test body",
        )
        session.add(email)
        session.commit()

        result = session.execute(select(Email)).scalar_one()
        assert result.user_id == user.id
        assert result.google_message_id == "msg-123"
        assert result.is_processed is False

    def test_user_has_emails_relationship(self, session: Session) -> None:
        """User should have emails relationship."""
        from src.models import Email, User

        user = User(firebase_uid="uid-123", email="test@example.com")
        session.add(user)
        session.commit()

        email = Email(
            user_id=user.id,
            google_message_id="msg-123",
            sender_email="boss@example.com",
        )
        session.add(email)
        session.commit()

        session.refresh(user)
        assert hasattr(user, "emails")
        assert len(user.emails) == 1
        assert user.emails[0].google_message_id == "msg-123"

    def test_user_has_contacts_relationship(self, session: Session) -> None:
        """User should have contacts relationship."""
        from src.models import Contact, User

        user = User(firebase_uid="uid-123", email="test@example.com")
        session.add(user)
        session.commit()

        contact = Contact(
            user_id=user.id,
            contact_email="boss@example.com",
        )
        session.add(contact)
        session.commit()

        session.refresh(user)
        assert hasattr(user, "contacts")
        assert len(user.contacts) == 1
        assert user.contacts[0].contact_email == "boss@example.com"

    def test_can_create_contact_context_with_contact(self, session: Session) -> None:
        """Should be able to create a contact context linked to a contact."""
        from src.models import Contact, ContactContext, User

        user = User(firebase_uid="uid-123", email="test@example.com")
        session.add(user)
        session.commit()

        contact = Contact(
            user_id=user.id,
            contact_email="boss@example.com",
            contact_name="Boss",
        )
        session.add(contact)
        session.commit()

        learned_patterns = (
            '{"contactCharacteristics": {"tone": "formal"}, "userReplyPatterns": {}}'
        )
        context = ContactContext(
            contact_id=contact.id,
            learned_patterns=learned_patterns,
        )
        session.add(context)
        session.commit()

        from sqlalchemy import select

        result = session.execute(select(ContactContext)).scalar_one()
        assert result.contact_id == contact.id
        assert result.learned_patterns == learned_patterns
        assert result.updated_at is not None

    def test_contact_has_context_relationship(self, session: Session) -> None:
        """Contact should have context relationship (one-to-one)."""
        from src.models import Contact, ContactContext, User

        user = User(firebase_uid="uid-123", email="test@example.com")
        session.add(user)
        session.commit()

        contact = Contact(
            user_id=user.id,
            contact_email="boss@example.com",
        )
        session.add(contact)
        session.commit()

        context = ContactContext(
            contact_id=contact.id,
            learned_patterns='{"test": true}',
        )
        session.add(context)
        session.commit()

        session.refresh(contact)
        assert hasattr(contact, "context")
        assert contact.context is not None
        assert contact.context.learned_patterns == '{"test": true}'

    def test_contact_context_deleted_on_contact_delete(self, session: Session) -> None:
        """ContactContext should be deleted when contact is deleted (CASCADE)."""
        from sqlalchemy import select

        from src.models import Contact, ContactContext, User

        user = User(firebase_uid="uid-123", email="test@example.com")
        session.add(user)
        session.commit()

        contact = Contact(
            user_id=user.id,
            contact_email="boss@example.com",
        )
        session.add(contact)
        session.commit()

        context = ContactContext(
            contact_id=contact.id,
            learned_patterns='{"test": true}',
        )
        session.add(context)
        session.commit()

        # Verify context exists
        result = session.execute(select(ContactContext)).scalars().all()
        assert len(result) == 1

        # Delete contact
        session.delete(contact)
        session.commit()

        # Verify context is also deleted
        result = session.execute(select(ContactContext)).scalars().all()
        assert len(result) == 0

    def test_email_reply_fields_in_database(self, session: Session) -> None:
        """Email reply fields should be persistable in the database."""
        from datetime import datetime, timezone

        from src.models import Email, User

        user = User(firebase_uid="uid-123", email="test@example.com")
        session.add(user)
        session.commit()

        now = datetime.now(timezone.utc)
        email = Email(
            user_id=user.id,
            google_message_id="msg-reply-test",
            sender_email="boss@example.com",
            reply_body="お世話になっております。ご連絡ありがとうございます。",
            reply_subject="Re: 重要なお知らせ",
            replied_at=now,
            reply_google_message_id="reply-msg-456",
        )
        session.add(email)
        session.commit()

        result = session.execute(
            select(Email).where(Email.google_message_id == "msg-reply-test")
        ).scalar_one()
        assert (
            result.reply_body == "お世話になっております。ご連絡ありがとうございます。"
        )
        assert result.reply_subject == "Re: 重要なお知らせ"
        assert result.replied_at is not None
        assert result.reply_google_message_id == "reply-msg-456"

    def test_email_reply_fields_null_by_default(self, session: Session) -> None:
        """Email reply fields should be null when not set."""
        from src.models import Email, User

        user = User(firebase_uid="uid-123", email="test@example.com")
        session.add(user)
        session.commit()

        email = Email(
            user_id=user.id,
            google_message_id="msg-no-reply",
            sender_email="boss@example.com",
        )
        session.add(email)
        session.commit()

        result = session.execute(
            select(Email).where(Email.google_message_id == "msg-no-reply")
        ).scalar_one()
        assert result.reply_body is None
        assert result.reply_subject is None
        assert result.replied_at is None
        assert result.reply_google_message_id is None

    def test_user_selected_character_id_persists_in_database(
        self, session: Session
    ) -> None:
        """selected_character_id should be persistable in the database."""
        from src.models import User

        user = User(
            firebase_uid="uid-char-test",
            email="char-test@example.com",
            selected_character_id="senpai",
        )
        session.add(user)
        session.commit()

        result = session.execute(
            select(User).where(User.firebase_uid == "uid-char-test")
        ).scalar_one()
        assert result.selected_character_id == "senpai"

    def test_user_selected_character_id_null_in_database(
        self, session: Session
    ) -> None:
        """selected_character_id should be null when not set."""
        from src.models import User

        user = User(
            firebase_uid="uid-char-null",
            email="char-null@example.com",
        )
        session.add(user)
        session.commit()

        result = session.execute(
            select(User).where(User.firebase_uid == "uid-char-null")
        ).scalar_one()
        assert result.selected_character_id is None

    def test_contact_learning_failed_at_field(self, session: Session) -> None:
        """Contact should have learning_failed_at field."""
        from datetime import datetime, timezone

        from src.models import Contact, User

        user = User(firebase_uid="uid-123", email="test@example.com")
        session.add(user)
        session.commit()

        contact = Contact(
            user_id=user.id,
            contact_email="boss@example.com",
            learning_failed_at=datetime.now(timezone.utc),
        )
        session.add(contact)
        session.commit()

        from sqlalchemy import select

        result = session.execute(select(Contact)).scalar_one()
        assert result.learning_failed_at is not None
