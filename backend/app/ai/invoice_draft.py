"""Draft invoice line items from a vet's free-text visit notes.

This is a small LangChain "chain": a prompt template feeds the notes and the
clinic's price list to Llama 3.1 8B (via Groq), and `.with_structured_output(...)`
asks it to answer in the exact shape of `LineItemCreate` instead of a paragraph.

Nothing here is saved to the database — callers get back proposed line items
for a human to review before adding them to a real invoice.
"""

import logging

from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel

from app.config import get_settings
from app.schemas.invoice import CommonLineItem, LineItemCreate

logger = logging.getLogger(__name__)

_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a veterinary billing assistant. Read the vet's visit notes and "
            "propose invoice line items for the services and products actually "
            "described. Reuse a description and price from the clinic's price list "
            "whenever a listed service matches; otherwise write a short description "
            "and leave unit_price_cents at your best estimate. Use quantity 1 unless "
            "the notes clearly call for more. Do not invent services the notes don't "
            "mention.\n\n"
            "Respond with ONLY a JSON object matching this schema, no other text:\n"
            '{{"items": [{{"description": string, "quantity": integer, '
            '"unit_price_cents": integer}}, ...]}}',
        ),
        (
            "human",
            "Clinic price list (description - price in cents):\n{catalog}\n\n"
            "Visit notes:\n{notes}",
        ),
    ]
)


class _DraftedLineItems(BaseModel):
    items: list[LineItemCreate]


def draft_line_items(notes: str, catalog: list[CommonLineItem]) -> list[LineItemCreate]:
    """Turn free-text visit notes into proposed invoice line items."""
    settings = get_settings()
    llm = ChatGroq(model="llama-3.1-8b-instant", api_key=settings.GROQ_API_KEY)
    # json_mode, not the with_structured_output default (function_calling) - this
    # model unreliably formats tool calls on Groq, but is solid at plain JSON when
    # the schema is spelled out in the prompt (which json_mode requires anyway).
    structured_llm = llm.with_structured_output(_DraftedLineItems, method="json_mode")

    catalog_text = "\n".join(f"- {item.description} - {item.unit_price_cents}" for item in catalog)
    if not catalog_text:
        catalog_text = "(no price history yet)"

    chain = _PROMPT | structured_llm
    logger.info("Calling Groq (llama-3.1-8b-instant) to draft invoice line items (notes_len=%d)", len(notes))
    try:
        result = chain.invoke({"catalog": catalog_text, "notes": notes})
    except Exception:
        logger.exception("Groq call failed while drafting invoice line items")
        raise
    logger.info("Drafted %d invoice line item(s)", len(result.items))
    return result.items
