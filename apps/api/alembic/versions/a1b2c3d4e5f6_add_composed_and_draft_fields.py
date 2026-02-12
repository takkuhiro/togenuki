"""add_composed_and_draft_fields

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-02-12 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add composed_body, composed_subject, google_draft_id columns to emails table."""
    op.add_column(
        "emails",
        sa.Column("composed_body", sa.Text(), nullable=True),
    )
    op.add_column(
        "emails",
        sa.Column("composed_subject", sa.Text(), nullable=True),
    )
    op.add_column(
        "emails",
        sa.Column("google_draft_id", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    """Remove composed_body, composed_subject, google_draft_id columns from emails table."""
    op.drop_column("emails", "google_draft_id")
    op.drop_column("emails", "composed_subject")
    op.drop_column("emails", "composed_body")
