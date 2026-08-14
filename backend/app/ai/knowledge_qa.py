"""Answer clinic-policy questions grounded in the ingested documents (RAG).

Retrieval: embed the question, then ask pgvector for the nearest chunks by
cosine distance - this is the "search first" step.
Generation: give the LLM the question plus the retrieved chunks and ask it to
answer using only that context, citing which document(s) it used.
"""

import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import embed_text
from app.config import get_settings
from app.models.knowledge import KnowledgeChunk
from app.schemas.knowledge import AskResponse

logger = logging.getLogger(__name__)

_TOP_K = 4

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a front-desk assistant answering questions about clinic "
            "policy. Answer using ONLY the context passages below - do not use "
            "outside knowledge, and do not guess. If the context doesn't contain "
            "the answer, say you don't know. List which document(s) the answer "
            "came from in `sources`, using their exact names as given.\n\n"
            "Respond with ONLY a JSON object matching this schema, no other text:\n"
            '{{"answer": string, "sources": [string, ...]}}',
        ),
        (
            "human",
            "Context passages:\n{context}\n\nQuestion: {question}",
        ),
    ]
)


def retrieve_chunks(
    db: Session, question: str, top_k: int = _TOP_K, document: str | None = None
) -> list[KnowledgeChunk]:
    """Find the stored chunks whose embedding is closest in meaning to the question.

    Pass `document` to restrict the search to one ingested document (metadata
    filtering) instead of searching across all of them - use this when the
    caller already knows which document is relevant, so a mediocre embedding
    ranking can't push the right chunk out of the top-k.
    """
    question_embedding = embed_text(question)
    stmt = select(KnowledgeChunk).order_by(KnowledgeChunk.embedding.cosine_distance(question_embedding))
    if document is not None:
        stmt = stmt.where(KnowledgeChunk.document == document)
    return list(db.execute(stmt.limit(top_k)).scalars().all())


def answer_question(db: Session, question: str) -> AskResponse:
    """Retrieve relevant chunks and ask the LLM to answer grounded in them."""
    chunks = retrieve_chunks(db, question)
    if not chunks:
        return AskResponse(answer="I don't have any clinic policy documents to check yet.", sources=[])

    context = "\n\n".join(f"[{chunk.document}] {chunk.content}" for chunk in chunks)

    settings = get_settings()
    llm = ChatGroq(model="llama-3.1-8b-instant", api_key=settings.GROQ_API_KEY)
    structured_llm = llm.with_structured_output(AskResponse, method="json_mode")

    chain = _PROMPT | structured_llm
    logger.info("Calling Groq (llama-3.1-8b-instant) to answer policy question (chunks=%d)", len(chunks))
    try:
        response = chain.invoke({"context": context, "question": question})
    except Exception:
        logger.exception("Groq call failed while answering policy question")
        raise
    return response
