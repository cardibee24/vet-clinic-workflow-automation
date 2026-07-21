"""Draft invoice line items from a vet's free-text visit notes.

This is a small LangChain "chain": a prompt template feeds the notes and the
clinic's price list to Gemini, and `.with_structured_output(...)` asks it
to answer in the exact shape of `LineItemCreate` instead of a paragraph.

Nothing here is saved to the database — callers get back proposed line items
for a human to review before adding them to a real invoice.
"""

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.config import get_settings
from app.schemas.invoice import CommonLineItem, LineItemCreate

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
            "mention.",
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
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.GOOGLE_API_KEY)
    structured_llm = llm.with_structured_output(_DraftedLineItems)

    catalog_text = "\n".join(f"- {item.description} - {item.unit_price_cents}" for item in catalog)
    if not catalog_text:
        catalog_text = "(no price history yet)"

    chain = _PROMPT | structured_llm
    result = chain.invoke({"catalog": catalog_text, "notes": notes})
    return result.items
