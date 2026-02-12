"""add_thread_id_and_reply_source

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-02-12 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: str | Sequence[str] | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add google_thread_id and reply_source columns to emails table."""
    op.add_column(
        "emails",
        sa.Column("google_thread_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "emails",
        sa.Column("reply_source", sa.String(32), nullable=True),
    )


def downgrade() -> None:
    """Remove google_thread_id and reply_source columns from emails table."""
    op.drop_column("emails", "reply_source")
    op.drop_column("emails", "google_thread_id")
