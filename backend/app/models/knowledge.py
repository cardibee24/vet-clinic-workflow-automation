from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin

# Dimension of the local sentence-transformers model (all-MiniLM-L6-v2) used
# by app.ai.embeddings. If the model changes, this must change too, and the
# table must be re-ingested (embeddings from different models aren't comparable).
EMBEDDING_DIM = 384


class KnowledgeChunk(Base, UUIDPKMixin, TimestampMixin):
    """A chunk of a clinic policy document, plus its embedding, for RAG retrieval."""

    __tablename__ = "knowledge_chunks"

    document: Mapped[str] = mapped_column(nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    content: Mapped[str] = mapped_column(nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
