"""add invoices

Revision ID: 634811b435a8
Revises: 3d6e2b2026dd
Create Date: 2026-07-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "634811b435a8"
down_revision: str | None = "3d6e2b2026dd"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

invoice_status = postgresql.ENUM("draft", "issued", "paid", "void", name="invoice_status", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    invoice_status.create(bind, checkfirst=True)

    op.create_table(
        "invoices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=True),
        sa.Column("status", invoice_status, server_default="draft", nullable=False),
        sa.Column("issued_at", sa.DateTime(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_invoices_clinic_id_clinics"),
        sa.ForeignKeyConstraint(["owner_id"], ["owners.id"], name="fk_invoices_owner_id_owners"),
        sa.ForeignKeyConstraint(
            ["appointment_id"], ["appointments.id"], name="fk_invoices_appointment_id_appointments"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_invoices"),
    )
    op.create_index("ix_invoices_clinic_id", "invoices", ["clinic_id"])
    op.create_index("ix_invoices_owner_id", "invoices", ["owner_id"])

    op.create_table(
        "invoice_line_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("unit_price_cents", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_invoice_line_items_clinic_id_clinics"),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["invoices.id"], name="fk_invoice_line_items_invoice_id_invoices"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_invoice_line_items"),
    )
    op.create_index("ix_invoice_line_items_clinic_id", "invoice_line_items", ["clinic_id"])
    op.create_index("ix_invoice_line_items_invoice_id", "invoice_line_items", ["invoice_id"])


def downgrade() -> None:
    op.drop_table("invoice_line_items")
    op.drop_table("invoices")
    invoice_status.drop(op.get_bind(), checkfirst=True)
