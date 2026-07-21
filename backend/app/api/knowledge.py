from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.knowledge_qa import answer_question
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.knowledge import AskRequest, AskResponse

router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(
    body: AskRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AskResponse:
    """Answer a clinic-policy question, grounded in the ingested documents (RAG)."""
    try:
        return answer_question(db, body.question)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI answering is unavailable right now. Check GOOGLE_API_KEY and try again.",
        ) from exc
