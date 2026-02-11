"""add_selected_character_id_to_users

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-10 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: str | Sequence[str] | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add selected_character_id column to users table."""
    op.add_column(
        "users",
        sa.Column("selected_character_id", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    """Remove selected_character_id column from users table."""
    op.drop_column("users", "selected_character_id")
