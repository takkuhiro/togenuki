"""add_reply_fields_to_emails

Revision ID: d4e5f6a7b8c9
Revises: c3a1b2d4e5f6
Create Date: 2026-02-07 09:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: str | Sequence[str] | None = "c3a1b2d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add reply-related columns to emails table."""
    op.add_column(
        "emails",
        sa.Column("reply_body", sa.Text(), nullable=True),
    )
    op.add_column(
        "emails",
        sa.Column("reply_subject", sa.Text(), nullable=True),
    )
    op.add_column(
        "emails",
        sa.Column("replied_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "emails",
        sa.Column("reply_google_message_id", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    """Remove reply-related columns from emails table."""
    op.drop_column("emails", "reply_google_message_id")
    op.drop_column("emails", "replied_at")
    op.drop_column("emails", "reply_subject")
    op.drop_column("emails", "reply_body")
