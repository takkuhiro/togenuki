"""migrate_to_uuid_v7

Revision ID: b8f2a3c91d04
Revises: 47c94c087902
Create Date: 2026-02-05 13:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8f2a3c91d04"
down_revision: str | Sequence[str] | None = "47c94c087902"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop existing tables and recreate with UUID v7 primary keys."""
    # Drop existing tables (in reverse order due to foreign keys)
    op.drop_index("idx_emails_google_message_id", "emails")
    op.drop_index("idx_emails_contact_id", "emails")
    op.drop_index("idx_emails_user_id", "emails")
    op.drop_table("emails")

    op.drop_index("idx_contacts_user_id", "contacts")
    op.drop_table("contacts")

    op.drop_index("idx_users_firebase_uid", "users")
    op.drop_table("users")

    # Recreate tables with UUID primary keys
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("firebase_uid", sa.String(128), unique=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("gmail_refresh_token", sa.Text(), nullable=True),
        sa.Column("gmail_access_token", sa.Text(), nullable=True),
        sa.Column("gmail_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gmail_history_id", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_users_firebase_uid", "users", ["firebase_uid"])

    op.create_table(
        "contacts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("gmail_query", sa.String(512), nullable=True),
        sa.Column(
            "is_learning_complete", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "contact_email", name="uq_contacts_user_email"),
    )
    op.create_index("idx_contacts_user_id", "contacts", ["user_id"])

    op.create_table(
        "emails",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "contact_id",
            UUID(as_uuid=True),
            sa.ForeignKey("contacts.id"),
            nullable=True,
        ),
        sa.Column("google_message_id", sa.String(255), unique=True, nullable=False),
        sa.Column("sender_email", sa.String(255), nullable=False),
        sa.Column("sender_name", sa.String(255), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("original_body", sa.Text(), nullable=True),
        sa.Column("converted_body", sa.Text(), nullable=True),
        sa.Column("audio_url", sa.String(1024), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_processed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_emails_user_id", "emails", ["user_id"])
    op.create_index("idx_emails_contact_id", "emails", ["contact_id"])
    op.create_index("idx_emails_google_message_id", "emails", ["google_message_id"])


def downgrade() -> None:
    """Revert to integer primary keys."""
    # Drop UUID tables
    op.drop_index("idx_emails_google_message_id", "emails")
    op.drop_index("idx_emails_contact_id", "emails")
    op.drop_index("idx_emails_user_id", "emails")
    op.drop_table("emails")

    op.drop_index("idx_contacts_user_id", "contacts")
    op.drop_table("contacts")

    op.drop_index("idx_users_firebase_uid", "users")
    op.drop_table("users")

    # Recreate with integer PKs
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("firebase_uid", sa.String(128), unique=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("gmail_refresh_token", sa.Text(), nullable=True),
        sa.Column("gmail_access_token", sa.Text(), nullable=True),
        sa.Column("gmail_token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gmail_history_id", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_users_firebase_uid", "users", ["firebase_uid"])

    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("contact_email", sa.String(255), nullable=False),
        sa.Column("contact_name", sa.String(255), nullable=True),
        sa.Column("gmail_query", sa.String(512), nullable=True),
        sa.Column(
            "is_learning_complete", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "contact_email", name="uq_contacts_user_email"),
    )
    op.create_index("idx_contacts_user_id", "contacts", ["user_id"])

    op.create_table(
        "emails",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "contact_id", sa.Integer(), sa.ForeignKey("contacts.id"), nullable=True
        ),
        sa.Column("google_message_id", sa.String(255), unique=True, nullable=False),
        sa.Column("sender_email", sa.String(255), nullable=False),
        sa.Column("sender_name", sa.String(255), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("original_body", sa.Text(), nullable=True),
        sa.Column("converted_body", sa.Text(), nullable=True),
        sa.Column("audio_url", sa.String(1024), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_processed", sa.Boolean(), server_default="false", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_emails_user_id", "emails", ["user_id"])
    op.create_index("idx_emails_contact_id", "emails", ["contact_id"])
    op.create_index("idx_emails_google_message_id", "emails", ["google_message_id"])
