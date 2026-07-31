"""add ticket_number to appointments

Revision ID: 5c8f1a3d9b2e
Revises: 29dff9e9307e
Create Date: 2026-07-23

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5c8f1a3d9b2e"
down_revision: str | None = "29dff9e9307e"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("appointments", sa.Column("ticket_number", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("appointments", "ticket_number")
