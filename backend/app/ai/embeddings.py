"""Local text-embedding helper, used for RAG retrieval.

This deliberately runs on this machine instead of calling a hosted embedding
API, so retrieval doesn't need a second provider key on top of the LLM's own.
The model's output size (384) must match app.models.knowledge.EMBEDDING_DIM;
if you swap models, re-run app.ai.knowledge_ingest and update both places.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

_MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache
def _model() -> SentenceTransformer:
    return SentenceTransformer(_MODEL_NAME)


def embed_text(text: str) -> list[float]:
    """Embed a single piece of text."""
    return embed_texts([text])[0]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts at once - more efficient than calling embed_text in a loop."""
    vectors = _model().encode(texts, normalize_embeddings=True)
    return [vector.tolist() for vector in vectors]
