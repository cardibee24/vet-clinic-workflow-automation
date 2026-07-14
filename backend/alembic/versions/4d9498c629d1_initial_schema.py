"""initial schema

Revision ID: 4d9498c629d1
Revises:
Create Date: 2026-07-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4d9498c629d1"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

user_role = postgresql.ENUM("vet", "tech", "front_desk", "admin", name="user_role")
appointment_status = postgresql.ENUM(
    "scheduled", "checked_in", "in_progress", "completed", "cancelled", "no_show",
    name="appointment_status",
)


def upgrade() -> None:
    bind = op.get_bind()
    user_role.create(bind, checkfirst=True)
    appointment_status.create(bind, checkfirst=True)

    op.create_table(
        "clinics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_clinics"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_users_clinic_id_clinics"),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_clinic_id", "users", ["clinic_id"])
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "owners",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_owners_clinic_id_clinics"),
        sa.PrimaryKeyConstraint("id", name="pk_owners"),
    )
    op.create_index("ix_owners_clinic_id", "owners", ["clinic_id"])

    op.create_table(
        "pets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("owner_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("species", sa.String(), nullable=False),
        sa.Column("breed", sa.String(), nullable=True),
        sa.Column("date_of_birth", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_pets_clinic_id_clinics"),
        sa.ForeignKeyConstraint(["owner_id"], ["owners.id"], name="fk_pets_owner_id_owners"),
        sa.PrimaryKeyConstraint("id", name="pk_pets"),
    )
    op.create_index("ix_pets_clinic_id", "pets", ["clinic_id"])
    op.create_index("ix_pets_owner_id", "pets", ["owner_id"])

    op.create_table(
        "appointments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("pet_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_user_id", sa.Uuid(), nullable=True),
        sa.Column("scheduled_start", sa.DateTime(), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(), nullable=False),
        sa.Column("status", appointment_status, server_default="scheduled", nullable=False),
        sa.Column("reason", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_appointments_clinic_id_clinics"),
        sa.ForeignKeyConstraint(["pet_id"], ["pets.id"], name="fk_appointments_pet_id_pets"),
        sa.ForeignKeyConstraint(["assigned_user_id"], ["users.id"], name="fk_appointments_assigned_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_appointments"),
    )
    op.create_index("ix_appointments_clinic_id", "appointments", ["clinic_id"])
    op.create_index("ix_appointments_pet_id", "appointments", ["pet_id"])


def downgrade() -> None:
    op.drop_table("appointments")
    op.drop_table("pets")
    op.drop_table("owners")
    op.drop_table("users")
    op.drop_table("clinics")
    appointment_status.drop(op.get_bind(), checkfirst=True)
    user_role.drop(op.get_bind(), checkfirst=True)
