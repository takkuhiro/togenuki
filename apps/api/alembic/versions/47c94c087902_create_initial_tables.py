"""create_initial_tables

Revision ID: 47c94c087902
Revises:
Create Date: 2026-02-04 13:05:46.431107

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "47c94c087902"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial tables: users, contacts, emails."""
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("firebase_uid", sa.String(128), unique=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("gmail_refresh_token", sa.Text(), nullable=True),
        sa.Column("gmail_access_token", sa.Text(), nullable=True),
        sa.Column(
            "gmail_token_expires_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_users_firebase_uid", "users", ["firebase_uid"])

    # Create contacts table
    op.create_table(
        "contacts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
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

    # Create emails table
    op.create_table(
        "emails",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
        ),
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
        sa.Column(
            "is_processed", sa.Boolean(), server_default="false", nullable=False
        ),
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
    """Drop all tables."""
    op.drop_index("idx_emails_google_message_id", "emails")
    op.drop_index("idx_emails_contact_id", "emails")
    op.drop_index("idx_emails_user_id", "emails")
    op.drop_table("emails")

    op.drop_index("idx_contacts_user_id", "contacts")
    op.drop_table("contacts")

    op.drop_index("idx_users_firebase_uid", "users")
    op.drop_table("users")
