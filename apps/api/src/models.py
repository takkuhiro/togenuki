"""SQLAlchemy ORM models for TogeNuki."""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from uuid6 import uuid7


def generate_uuid7() -> UUID:
    """Generate a new UUID v7."""
    return uuid7()


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class User(Base):
    """User model for storing user information and OAuth tokens."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    gmail_refresh_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    gmail_access_token: Mapped[str | None] = mapped_column(Text, nullable=True)
    gmail_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    gmail_history_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    emails: Mapped[list["Email"]] = relationship("Email", back_populates="user")
    contacts: Mapped[list["Contact"]] = relationship("Contact", back_populates="user")

    __table_args__ = (Index("idx_users_firebase_uid", "firebase_uid"),)


class Contact(Base):
    """Contact model for registered email contacts."""

    __tablename__ = "contacts"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gmail_query: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_learning_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    learning_failed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="contacts")
    emails: Mapped[list["Email"]] = relationship("Email", back_populates="contact")
    context: Mapped[Optional["ContactContext"]] = relationship(
        "ContactContext", back_populates="contact", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_contacts_user_id", "user_id"),
        # Unique constraint on user_id + contact_email is handled by migration
    )


class ContactContext(Base):
    """ContactContext model for storing learned patterns from email analysis."""

    __tablename__ = "contact_context"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    contact_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    learned_patterns: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    contact: Mapped["Contact"] = relationship("Contact", back_populates="context")

    __table_args__ = (Index("idx_contact_context_contact_id", "contact_id"),)


class Email(Base):
    """Email model for storing email data and conversion results."""

    __tablename__ = "emails"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=generate_uuid7
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    contact_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("contacts.id"), nullable=True
    )
    google_message_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    converted_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="emails")
    contact: Mapped[Optional["Contact"]] = relationship(
        "Contact", back_populates="emails"
    )

    __table_args__ = (
        Index("idx_emails_user_id", "user_id"),
        Index("idx_emails_contact_id", "contact_id"),
        Index("idx_emails_google_message_id", "google_message_id"),
    )
