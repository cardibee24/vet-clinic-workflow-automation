from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.ai.triage_graph import run_triage
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.triage import TriageRequest, TriageResponse

router = APIRouter()


@router.post("", response_model=TriageResponse)
def triage(
    body: TriageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TriageResponse:
    """Assign an urgency tier to a reported set of symptoms, per the clinic's
    triage protocol - or ask a follow-up question if the description is too
    vague to triage."""
    try:
        result = run_triage(db, body.symptoms)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI triage is unavailable right now. Check GROQ_API_KEY and try again.",
        ) from exc

    return TriageResponse(
        tier=result["tier"],
        reasoning=result["reasoning"],
        needs_more_info=result["needs_more_info"],
        follow_up_question=result["follow_up_question"],
    )
