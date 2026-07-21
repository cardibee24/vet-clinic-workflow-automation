"""One-time (re-run whenever the documents change) ingestion of clinic policy
documents into the knowledge_chunks table for RAG retrieval.

Run with:
    python -m app.ai.knowledge_ingest
"""

from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.ai.embeddings import embed_texts
from app.db.session import SessionLocal
from app.models.knowledge import KnowledgeChunk

_DOCS_DIR = Path(__file__).parent / "knowledge"

_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)


def ingest_documents(db: Session) -> int:
    """Chunk, embed, and store every document in app/ai/knowledge/.

    Replaces any existing chunks for a document, so this is safe to re-run
    after editing a document. Returns the total number of chunks stored.
    """
    total_chunks = 0
    for doc_path in sorted(_DOCS_DIR.glob("*.md")):
        document_name = doc_path.stem
        db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document == document_name))

        chunks = _splitter.split_text(doc_path.read_text(encoding="utf-8"))
        embeddings = embed_texts(chunks)
        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True)):
            db.add(KnowledgeChunk(document=document_name, chunk_index=index, content=chunk, embedding=embedding))
        total_chunks += len(chunks)

    db.commit()
    return total_chunks


if __name__ == "__main__":
    with SessionLocal() as session:
        count = ingest_documents(session)
        print(f"Ingested {count} chunks from {_DOCS_DIR}")
