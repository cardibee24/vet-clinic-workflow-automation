"""add visit_notes to appointments

Revision ID: b1d4e7f2a9c3
Revises: a8c3f2e91b4d
Create Date: 2026-07-19

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1d4e7f2a9c3"
down_revision: str | None = "a8c3f2e91b4d"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("appointments", sa.Column("visit_notes", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("appointments", "visit_notes")
