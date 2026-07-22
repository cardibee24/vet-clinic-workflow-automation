"""Symptom-triage assistant - a small LangGraph graph.

Combines two things already built elsewhere in this project:
  - RAG retrieval (app.ai.knowledge_qa.retrieve_chunks), scoped to the
    triage protocol document
  - an LLM decision call (LangChain chain, same pattern as app.ai.invoice_draft)

The graph itself is the new part: a flowchart with one conditional branch -
if the reported symptoms are too vague to triage, stop and ask a follow-up
question instead of asking the LLM to guess.

    check_description --(too vague)--> END (follow_up_question set)
           |
      (has enough detail)
           v
    retrieve_protocol -> decide_tier -> END
"""

from typing import TypedDict

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langgraph.graph import END, StateGraph
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.ai.knowledge_qa import retrieve_chunks
from app.config import get_settings

_MIN_DESCRIPTION_LENGTH = 15

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are triaging a walk-in or phone call at a vet clinic, using ONLY "
            "the triage protocol excerpts below - do not use outside knowledge. "
            "Assign the urgency tier (1, 2, or 3) that the reported symptoms match. "
            "If the symptoms could match more than one tier, always choose the more "
            "urgent (lower-numbered) tier, per the protocol. Only set needs_more_info "
            "to true if the description is too vague to match any tier's criteria at "
            "all - not merely because you're unsure between two tiers.\n\n"
            "Respond with ONLY a JSON object matching this schema, no other text:\n"
            '{{"tier": integer or null, "reasoning": string, "needs_more_info": '
            'boolean, "follow_up_question": string or null}}',
        ),
        (
            "human",
            "Triage protocol excerpts:\n{protocol}\n\nSymptoms reported: {symptoms}",
        ),
    ]
)


class TriageDecision(BaseModel):
    tier: int | None
    reasoning: str
    needs_more_info: bool
    follow_up_question: str | None


class TriageState(TypedDict):
    symptoms: str
    protocol_context: str
    tier: int | None
    reasoning: str | None
    needs_more_info: bool
    follow_up_question: str | None


def _check_description(state: TriageState) -> TriageState:
    """Plain code decision - no LLM call. Screens out descriptions too short
    to triage before spending a model call on them."""
    if len(state["symptoms"].strip()) < _MIN_DESCRIPTION_LENGTH:
        return {
            **state,
            "needs_more_info": True,
            "follow_up_question": "Can you describe the symptoms in a bit more detail?",
        }
    return state


def _route_after_check(state: TriageState) -> str:
    return "end" if state["needs_more_info"] else "retrieve_protocol"


def _decide_tier(state: TriageState) -> TriageState:
    settings = get_settings()
    llm = ChatGroq(model="llama-3.1-8b-instant", api_key=settings.GROQ_API_KEY)
    structured_llm = llm.with_structured_output(TriageDecision, method="json_mode")

    chain = _PROMPT | structured_llm
    decision: TriageDecision = chain.invoke({"protocol": state["protocol_context"], "symptoms": state["symptoms"]})

    return {
        **state,
        "tier": decision.tier,
        "reasoning": decision.reasoning,
        "needs_more_info": decision.needs_more_info,
        "follow_up_question": decision.follow_up_question,
    }


def build_triage_graph(db: Session):
    """Build the graph. Takes `db` so the retrieval node can query it - this
    is a closure rather than a state field because a DB session isn't
    serializable data, it's a resource."""

    def _retrieve_protocol(state: TriageState) -> TriageState:
        # Scoped to the triage protocol specifically (metadata filtering) rather
        # than searching all documents - this is what actually fixed the
        # "seizure" query missing the Tier 1 chunk during testing (see
        # knowledge_qa.retrieve_chunks docstring).
        chunks = retrieve_chunks(db, state["symptoms"], top_k=5, document="triage_protocol")
        context = "\n\n".join(chunk.content for chunk in chunks)
        return {**state, "protocol_context": context}

    graph = StateGraph(TriageState)
    graph.add_node("check_description", _check_description)
    graph.add_node("retrieve_protocol", _retrieve_protocol)
    graph.add_node("decide_tier", _decide_tier)

    graph.set_entry_point("check_description")
    graph.add_conditional_edges(
        "check_description",
        _route_after_check,
        {"end": END, "retrieve_protocol": "retrieve_protocol"},
    )
    graph.add_edge("retrieve_protocol", "decide_tier")
    graph.add_edge("decide_tier", END)

    return graph.compile()


def run_triage(db: Session, symptoms: str) -> TriageState:
    """Run the triage graph to completion for one submitted description."""
    graph = build_triage_graph(db)
    initial_state: TriageState = {
        "symptoms": symptoms,
        "protocol_context": "",
        "tier": None,
        "reasoning": None,
        "needs_more_info": False,
        "follow_up_question": None,
    }
    return graph.invoke(initial_state)
