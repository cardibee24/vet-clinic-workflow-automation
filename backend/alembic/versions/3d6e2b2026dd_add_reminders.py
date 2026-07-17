"""add reminders

Revision ID: 3d6e2b2026dd
Revises: 12a5ab6c2ce9
Create Date: 2026-07-17

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3d6e2b2026dd"
down_revision: str | None = "12a5ab6c2ce9"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

reminder_channel = postgresql.ENUM("email", "sms", name="reminder_channel", create_type=False)
reminder_status = postgresql.ENUM(
    "pending", "sent", "failed", "cancelled", name="reminder_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    reminder_channel.create(bind, checkfirst=True)
    reminder_status.create(bind, checkfirst=True)

    op.create_table(
        "reminders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("clinic_id", sa.Uuid(), nullable=False),
        sa.Column("appointment_id", sa.Uuid(), nullable=False),
        sa.Column("channel", reminder_channel, nullable=False),
        sa.Column("send_at", sa.DateTime(), nullable=False),
        sa.Column("status", reminder_status, server_default="pending", nullable=False),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["clinic_id"], ["clinics.id"], name="fk_reminders_clinic_id_clinics"),
        sa.ForeignKeyConstraint(
            ["appointment_id"], ["appointments.id"], name="fk_reminders_appointment_id_appointments"
        ),
        sa.PrimaryKeyConstraint("id", name="pk_reminders"),
    )
    op.create_index("ix_reminders_clinic_id", "reminders", ["clinic_id"])
    op.create_index("ix_reminders_appointment_id", "reminders", ["appointment_id"])


def downgrade() -> None:
    op.drop_table("reminders")
    reminder_status.drop(op.get_bind(), checkfirst=True)
    reminder_channel.drop(op.get_bind(), checkfirst=True)
