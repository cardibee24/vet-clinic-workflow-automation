"""narrow user roles to vet and owner

Revision ID: a1c9f0e8b2d4
Revises: 634811b435a8
Create Date: 2026-07-17

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1c9f0e8b2d4"
down_revision: str | None = "634811b435a8"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TYPE user_role RENAME TO user_role_old")
    op.execute("CREATE TYPE user_role AS ENUM ('vet', 'owner')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE user_role "
        "USING (CASE WHEN role::text = 'vet' THEN 'vet' ELSE 'owner' END)::user_role"
    )
    op.execute("DROP TYPE user_role_old")


def downgrade() -> None:
    op.execute("ALTER TYPE user_role RENAME TO user_role_new")
    op.execute("CREATE TYPE user_role AS ENUM ('vet', 'tech', 'front_desk', 'admin')")
    op.execute(
        "ALTER TABLE users ALTER COLUMN role TYPE user_role "
        "USING (CASE WHEN role::text = 'vet' THEN 'vet' ELSE 'admin' END)::user_role"
    )
    op.execute("DROP TYPE user_role_new")
