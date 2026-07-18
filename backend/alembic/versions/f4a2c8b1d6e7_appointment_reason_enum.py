"""convert appointments.reason from free text to a fixed enum

Revision ID: f4a2c8b1d6e7
Revises: e2f8b4a1c9d3
Create Date: 2026-07-18

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f4a2c8b1d6e7"
down_revision: str | None = "e2f8b4a1c9d3"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

appointment_reason = postgresql.ENUM(
    "checkup",
    "vaccination",
    "surgery",
    "dental",
    "follow_up",
    "emergency",
    "diagnostic",
    name="appointment_reason",
    create_type=False,
)

# Best-effort mapping from old free-text reason to the new fixed categories.
# Anything that doesn't match a pattern becomes NULL - reason was always
# optional, and there's no reliable way to categorize arbitrary old text.
_UPGRADE_CASE_SQL = """
    UPDATE appointments SET reason_new = (
        CASE
            WHEN reason ILIKE '%%vaccin%%' THEN 'vaccination'
            WHEN reason ILIKE '%%surger%%' THEN 'surgery'
            WHEN reason ILIKE '%%dental%%' OR reason ILIKE '%%tooth%%' OR reason ILIKE '%%teeth%%'
                THEN 'dental'
            WHEN reason ILIKE '%%follow%%' THEN 'follow_up'
            WHEN reason ILIKE '%%emergen%%' OR reason ILIKE '%%urgent%%' THEN 'emergency'
            WHEN reason ILIKE '%%diagnos%%' OR reason ILIKE '%%x-ray%%' OR reason ILIKE '%%xray%%'
                OR reason ILIKE '%%lab%%' OR reason ILIKE '%%ultrasound%%' THEN 'diagnostic'
            WHEN reason ILIKE '%%check%%' OR reason ILIKE '%%wellness%%' OR reason ILIKE '%%annual%%'
                THEN 'checkup'
            ELSE NULL
        END
    )::appointment_reason
    WHERE reason IS NOT NULL
"""


def upgrade() -> None:
    bind = op.get_bind()
    appointment_reason.create(bind, checkfirst=True)

    op.add_column("appointments", sa.Column("reason_new", appointment_reason, nullable=True))
    op.execute(_UPGRADE_CASE_SQL)
    op.drop_column("appointments", "reason")
    op.alter_column("appointments", "reason_new", new_column_name="reason")


def downgrade() -> None:
    op.add_column("appointments", sa.Column("reason_old", sa.String(), nullable=True))
    op.execute("UPDATE appointments SET reason_old = reason::text WHERE reason IS NOT NULL")
    op.drop_column("appointments", "reason")
    op.alter_column("appointments", "reason_old", new_column_name="reason")
    appointment_reason.drop(op.get_bind(), checkfirst=True)
