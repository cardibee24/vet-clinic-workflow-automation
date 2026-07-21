"""add knowledge chunks

Revision ID: 29dff9e9307e
Revises: a3f1c6b9d2e4
Create Date: 2026-07-21 16:43:58.965116

"""

from collections.abc import Sequence

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "29dff9e9307e"
down_revision: str | None = "a3f1c6b9d2e4"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

# Must match app.models.knowledge.EMBEDDING_DIM (the local sentence-transformers
# model's output size).
EMBEDDING_DIM = 384


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "knowledge_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("document", sa.String(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_knowledge_chunks"),
    )
    op.create_index("ix_knowledge_chunks_document", "knowledge_chunks", ["document"])
    # Approximate nearest-neighbor index for cosine similarity search.
    op.execute(
        "CREATE INDEX ix_knowledge_chunks_embedding ON knowledge_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_table("knowledge_chunks")
    op.execute("DROP EXTENSION IF EXISTS vector")
