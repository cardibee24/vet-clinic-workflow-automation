"""add payment_method and paid_at to invoices

Revision ID: a8c3f2e91b4d
Revises: f4a2c8b1d6e7
Create Date: 2026-07-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8c3f2e91b4d"
down_revision: str | None = "f4a2c8b1d6e7"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

payment_method = postgresql.ENUM(
    "cash", "card", "bank_transfer", "other", name="payment_method", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    payment_method.create(bind, checkfirst=True)

    op.add_column("invoices", sa.Column("paid_at", sa.DateTime(), nullable=True))
    op.add_column("invoices", sa.Column("payment_method", payment_method, nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "payment_method")
    op.drop_column("invoices", "paid_at")
    payment_method.drop(op.get_bind(), checkfirst=True)
