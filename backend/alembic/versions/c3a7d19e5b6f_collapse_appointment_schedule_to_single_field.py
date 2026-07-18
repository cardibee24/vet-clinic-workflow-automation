"""collapse appointment scheduled_start/scheduled_end into scheduled_at

Revision ID: c3a7d19e5b6f
Revises: 9b1d4e6a2f10
Create Date: 2026-07-18

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3a7d19e5b6f"
down_revision: str | None = "9b1d4e6a2f10"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("appointments", "scheduled_start", new_column_name="scheduled_at")
    op.drop_column("appointments", "scheduled_end")


def downgrade() -> None:
    op.alter_column("appointments", "scheduled_at", new_column_name="scheduled_start")
    # Original end time is gone; default to 30 minutes after start so the column can be non-nullable again.
    op.add_column("appointments", sa.Column("scheduled_end", sa.DateTime(), nullable=True))
    op.execute("UPDATE appointments SET scheduled_end = scheduled_start + INTERVAL '30 minutes'")
    op.alter_column("appointments", "scheduled_end", nullable=False)
