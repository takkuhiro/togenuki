"""add_contact_context_and_learning_failed_at

Revision ID: c3a1b2d4e5f6
Revises: b8f2a3c91d04
Create Date: 2026-02-05 15:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3a1b2d4e5f6"
down_revision: str | Sequence[str] | None = "b8f2a3c91d04"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add contact_context table and learning_failed_at column to contacts."""
    # Add learning_failed_at column to contacts table
    op.add_column(
        "contacts",
        sa.Column("learning_failed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create contact_context table
    op.create_table(
        "contact_context",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "contact_id",
            UUID(as_uuid=True),
            sa.ForeignKey("contacts.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("learned_patterns", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_contact_context_contact_id", "contact_context", ["contact_id"])


def downgrade() -> None:
    """Remove contact_context table and learning_failed_at column."""
    op.drop_index("idx_contact_context_contact_id", "contact_context")
    op.drop_table("contact_context")
    op.drop_column("contacts", "learning_failed_at")
