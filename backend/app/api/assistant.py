from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.assistant_graph import run_assistant
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.assistant import AssistantRequest, AssistantResponse

router = APIRouter()


@router.post("", response_model=AssistantResponse)
def ask_assistant(
    body: AssistantRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssistantResponse:
    """Single entry point that routes between clinic-policy Q&A (RAG) and
    appointment-availability checking, based on what the message is asking."""
    try:
        result = run_assistant(db, body.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assistant is unavailable right now. Check GOOGLE_API_KEY and try again.",
        ) from exc

    return AssistantResponse(intent=result["intent"] or "policy", reply=result["reply"] or "")
