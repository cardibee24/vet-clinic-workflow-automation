"""Answer clinic-policy questions grounded in the ingested documents (RAG).

Retrieval: embed the question, then ask pgvector for the nearest chunks by
cosine distance - this is the "search first" step.
Generation: give the LLM the question plus the retrieved chunks and ask it to
answer using only that context, citing which document(s) it used.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.embeddings import embed_text
from app.config import get_settings
from app.models.knowledge import KnowledgeChunk
from app.schemas.knowledge import AskResponse

_TOP_K = 4

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a front-desk assistant answering questions about clinic "
            "policy. Answer using ONLY the context passages below - do not use "
            "outside knowledge, and do not guess. If the context doesn't contain "
            "the answer, say you don't know. List which document(s) the answer "
            "came from in `sources`, using their exact names as given.",
        ),
        (
            "human",
            "Context passages:\n{context}\n\nQuestion: {question}",
        ),
    ]
)


def retrieve_chunks(db: Session, question: str, top_k: int = _TOP_K) -> list[KnowledgeChunk]:
    """Find the stored chunks whose embedding is closest in meaning to the question."""
    question_embedding = embed_text(question)
    stmt = select(KnowledgeChunk).order_by(KnowledgeChunk.embedding.cosine_distance(question_embedding)).limit(top_k)
    return list(db.execute(stmt).scalars().all())


def answer_question(db: Session, question: str) -> AskResponse:
    """Retrieve relevant chunks and ask the LLM to answer grounded in them."""
    chunks = retrieve_chunks(db, question)
    if not chunks:
        return AskResponse(answer="I don't have any clinic policy documents to check yet.", sources=[])

    context = "\n\n".join(f"[{chunk.document}] {chunk.content}" for chunk in chunks)

    settings = get_settings()
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.GOOGLE_API_KEY)
    structured_llm = llm.with_structured_output(AskResponse)

    chain = _PROMPT | structured_llm
    return chain.invoke({"context": context, "question": question})
