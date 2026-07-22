from pydantic import BaseModel


class TriageRequest(BaseModel):
    symptoms: str


class TriageResponse(BaseModel):
    tier: int | None
    reasoning: str | None
    needs_more_info: bool
    follow_up_question: str | None
