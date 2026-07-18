"""drop multi-tenancy (clinic_id, clinics table)

Revision ID: 9b1d4e6a2f10
Revises: 7a90c7539f23
Create Date: 2026-07-18

"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b1d4e6a2f10"
down_revision: str | None = "7a90c7539f23"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# (table_name, fk_name, index_name)
_TENANT_SCOPED_TABLES = [
    ("users", "fk_users_clinic_id_clinics", "ix_users_clinic_id"),
    ("owners", "fk_owners_clinic_id_clinics", "ix_owners_clinic_id"),
    ("pets", "fk_pets_clinic_id_clinics", "ix_pets_clinic_id"),
    ("appointments", "fk_appointments_clinic_id_clinics", "ix_appointments_clinic_id"),
    ("reminders", "fk_reminders_clinic_id_clinics", "ix_reminders_clinic_id"),
    ("invoices", "fk_invoices_clinic_id_clinics", "ix_invoices_clinic_id"),
    ("invoice_line_items", "fk_invoice_line_items_clinic_id_clinics", "ix_invoice_line_items_clinic_id"),
]


def upgrade() -> None:
    for table, fk_name, index_name in _TENANT_SCOPED_TABLES:
        op.drop_constraint(fk_name, table, type_="foreignkey")
        op.drop_index(index_name, table_name=table)
        op.drop_column(table, "clinic_id")

    op.drop_table("clinics")


def downgrade() -> None:
    op.create_table(
        "clinics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_clinics"),
    )

    # There is no way to recover which clinic each row originally belonged to
    # (that information no longer exists), so downgrade backfills everything
    # onto a single placeholder clinic.
    default_clinic_id = uuid.uuid4()
    op.execute(
        sa.text("INSERT INTO clinics (id, name) VALUES (:id, :name)").bindparams(
            id=default_clinic_id, name="Default Clinic"
        )
    )

    for table, fk_name, index_name in _TENANT_SCOPED_TABLES:
        op.add_column(table, sa.Column("clinic_id", sa.Uuid(), nullable=True))
        op.execute(
            sa.text(f"UPDATE {table} SET clinic_id = :clinic_id").bindparams(clinic_id=default_clinic_id)
        )
        op.alter_column(table, "clinic_id", nullable=False)
        op.create_foreign_key(fk_name, table, "clinics", ["clinic_id"], ["id"])
        op.create_index(index_name, table, ["clinic_id"])
