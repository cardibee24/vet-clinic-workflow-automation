"""add prescription to appointments

Revision ID: d7e3f9c1a4b8
Revises: b1d4e7f2a9c3
Create Date: 2026-07-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7e3f9c1a4b8"
down_revision: str | None = "b1d4e7f2a9c3"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("appointments", sa.Column("prescription", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("appointments", "prescription")
