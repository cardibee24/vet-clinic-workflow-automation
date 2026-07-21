"""add synced_vet_notes to invoices

Revision ID: a3f1c6b9d2e4
Revises: d7e3f9c1a4b8
Create Date: 2026-07-21

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a3f1c6b9d2e4"
down_revision: str | None = "d7e3f9c1a4b8"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("synced_vet_notes", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "synced_vet_notes")
