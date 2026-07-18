"""add checked_in_at to appointments

Revision ID: 7a90c7539f23
Revises: a1c9f0e8b2d4
Create Date: 2026-07-17

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a90c7539f23"
down_revision: str | None = "a1c9f0e8b2d4"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("appointments", sa.Column("checked_in_at", sa.DateTime(), nullable=True))
    # Backfill: approximate check-in time with updated_at for rows already checked in,
    # since updated_at was the only signal before this column existed.
    op.execute("UPDATE appointments SET checked_in_at = updated_at WHERE status = 'checked_in'")


def downgrade() -> None:
    op.drop_column("appointments", "checked_in_at")
