"""SQLAlchemy ORM models for TogeNuki."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class User(Base):
    """User model for storing user information and OAuth tokens."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    gmail_refresh_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gmail_access_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gmail_token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    emails: Mapped[List["Email"]] = relationship("Email", back_populates="user")
    contacts: Mapped[List["Contact"]] = relationship("Contact", back_populates="user")

    __table_args__ = (Index("idx_users_firebase_uid", "firebase_uid"),)


class Contact(Base):
    """Contact model for registered email contacts."""

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gmail_query: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_learning_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="contacts")
    emails: Mapped[List["Email"]] = relationship("Email", back_populates="contact")

    __table_args__ = (
        Index("idx_contacts_user_id", "user_id"),
        # Unique constraint on user_id + contact_email is handled by migration
    )


class Email(Base):
    """Email model for storing email data and conversion results."""

    __tablename__ = "emails"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    contact_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("contacts.id"), nullable=True
    )
    google_message_id: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    converted_body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    audio_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(
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
