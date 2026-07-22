"""A single assistant that routes between three capabilities via LangGraph.

    classify_intent
          |
    +-----+------+------+
  policy       booking   triage
    |             |         |
answer_policy  handle_   handle_triage
  (RAG, from     booking   (calls app.ai.triage_graph.run_triage -
  knowledge_qa) (extract    a graph node reusing a whole other graph)
    |          date/time,      |
    |          then check/     |
    |          suggest slots)  |
    +-------------+------------+
                  v
                 END

This is the "router" pattern: one classifier node picks which branch handles
the request, rather than every message taking the same fixed path (that
fixed-path shape is what app.ai.knowledge_qa alone does).

The booking branch only checks/suggests availability - it does not create a
real appointment, since that would need resolving an owner/pet name from
free text first, which is a separate feature.
"""

from datetime import datetime, timedelta
from typing import Literal, TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.knowledge_qa import answer_question
from app.ai.triage_graph import run_triage
from app.config import get_settings
from app.models.appointment import Appointment, AppointmentStatus

_SLOT_MINUTES = 30
_BUSINESS_HOURS = (9, 17)
_MAX_SUGGESTIONS = 3

_INTENT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Classify the user's message as one of:\n"
            "- `policy`: a question about clinic rules, vaccines, cancellations, "
            "or procedures\n"
            "- `booking`: a request to schedule, book, or check availability for "
            "an appointment\n"
            "- `triage`: describes a pet's symptoms or condition, asking how "
            "urgent it is or what to do about it\n\n"
            "Respond with ONLY a JSON object matching this schema, no other text:\n"
            '{{"intent": "policy" or "booking" or "triage"}}',
        ),
        ("human", "{message}"),
    ]
)

_BOOKING_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Extract the requested appointment date/time and reason from the "
            "message. Today's date is {today}. If the message doesn't clearly "
            "state a date and time, set needs_clarification to true and write a "
            "specific clarifying question rather than guessing.\n\n"
            "Respond with ONLY a JSON object matching this schema, no other text:\n"
            '{{"requested_datetime": ISO 8601 datetime string or null, "reason": '
            'string or null, "needs_clarification": boolean, "clarifying_question": '
            'string or null}}',
        ),
        ("human", "{message}"),
    ]
)


class IntentClassification(BaseModel):
    intent: Literal["policy", "booking", "triage"]


class BookingExtraction(BaseModel):
    requested_datetime: datetime | None
    reason: str | None
    needs_clarification: bool
    clarifying_question: str | None


class AssistantState(TypedDict):
    message: str
    intent: str | None
    reply: str | None


def _classify_intent(state: AssistantState) -> AssistantState:
    settings = get_settings()
    llm = ChatGroq(model="llama-3.1-8b-instant", api_key=settings.GROQ_API_KEY)
    structured_llm = llm.with_structured_output(IntentClassification, method="json_mode")
    chain = _INTENT_PROMPT | structured_llm
    result: IntentClassification = chain.invoke({"message": state["message"]})
    return {**state, "intent": result.intent}


def _route_by_intent(state: AssistantState) -> str:
    return state["intent"] or "policy"


def _is_slot_taken(db: Session, when: datetime) -> bool:
    window_start = when - timedelta(minutes=_SLOT_MINUTES // 2)
    window_end = when + timedelta(minutes=_SLOT_MINUTES // 2)
    stmt = (
        select(Appointment.id)
        .where(
            Appointment.scheduled_at >= window_start,
            Appointment.scheduled_at < window_end,
            Appointment.status.notin_([AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]),
        )
        .limit(1)
    )
    return db.execute(stmt).first() is not None


def _suggest_available_times(db: Session, requested: datetime) -> list[datetime]:
    """Look for open slots later the same business day, in fixed increments."""
    suggestions: list[datetime] = []
    day_start = requested.replace(hour=_BUSINESS_HOURS[0], minute=0, second=0, microsecond=0)
    day_end = requested.replace(hour=_BUSINESS_HOURS[1], minute=0, second=0, microsecond=0)
    candidate = max(requested, day_start)
    while candidate < day_end and len(suggestions) < _MAX_SUGGESTIONS:
        candidate += timedelta(minutes=_SLOT_MINUTES)
        if candidate < day_end and not _is_slot_taken(db, candidate):
            suggestions.append(candidate)
    return suggestions


def build_assistant_graph(db: Session):
    def _answer_policy(state: AssistantState) -> AssistantState:
        result = answer_question(db, state["message"])
        reply = result.answer
        if result.sources:
            reply += f" (Source: {', '.join(result.sources)})"
        return {**state, "reply": reply}

    def _handle_booking(state: AssistantState) -> AssistantState:
        settings = get_settings()
        llm = ChatGroq(model="llama-3.1-8b-instant", api_key=settings.GROQ_API_KEY)
        structured_llm = llm.with_structured_output(BookingExtraction, method="json_mode")
        chain = _BOOKING_PROMPT | structured_llm
        extraction: BookingExtraction = chain.invoke(
            {"message": state["message"], "today": datetime.now().strftime("%A, %B %d %Y")}
        )

        if extraction.needs_clarification or extraction.requested_datetime is None:
            reply = extraction.clarifying_question or "What date and time did you have in mind?"
            return {**state, "reply": reply}

        if not _is_slot_taken(db, extraction.requested_datetime):
            reply = (
                f"{extraction.requested_datetime.strftime('%A, %B %d at %I:%M %p')} is available. "
                "(This only checks availability - no appointment has been booked.)"
            )
        else:
            alternatives = _suggest_available_times(db, extraction.requested_datetime)
            if alternatives:
                times = ", ".join(t.strftime("%I:%M %p") for t in alternatives)
                reply = f"That time is already booked. Nearby open times the same day: {times}."
            else:
                reply = "That time is already booked, and there's no other open slot later that day."

        return {**state, "reply": reply}

    def _handle_triage(state: AssistantState) -> AssistantState:
        result = run_triage(db, state["message"])
        if result["needs_more_info"]:
            reply = result["follow_up_question"] or "Can you describe the symptoms in more detail?"
        else:
            reply = f"Tier {result['tier']}. {result['reasoning']}"
        return {**state, "reply": reply}

    graph = StateGraph(AssistantState)
    graph.add_node("classify_intent", _classify_intent)
    graph.add_node("answer_policy", _answer_policy)
    graph.add_node("handle_booking", _handle_booking)
    graph.add_node("handle_triage", _handle_triage)

    graph.set_entry_point("classify_intent")
    graph.add_conditional_edges(
        "classify_intent",
        _route_by_intent,
        {"policy": "answer_policy", "booking": "handle_booking", "triage": "handle_triage"},
    )
    graph.add_edge("answer_policy", END)
    graph.add_edge("handle_booking", END)
    graph.add_edge("handle_triage", END)

    return graph.compile()


def run_assistant(db: Session, message: str) -> AssistantState:
    graph = build_assistant_graph(db)
    initial_state: AssistantState = {"message": message, "intent": None, "reply": None}
    return graph.invoke(initial_state)
