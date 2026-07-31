"""Shared invoice/appointment logic used by both the invoices and appointments
routers - keeping it here (rather than duplicated, or one router importing the
other) avoids a circular import between the two.
"""

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.invoice_draft import draft_line_items
from app.models.appointment import Appointment
from app.models.invoice import Invoice, InvoiceLineItem
from app.schemas.invoice import CommonLineItem

logger = logging.getLogger(__name__)


def appointment_notes_text(appointment: Appointment) -> str | None:
    sections = []
    if appointment.visit_notes:
        sections.append(f"Description: {appointment.visit_notes}")
    if appointment.prescription:
        sections.append(f"Prescription: {appointment.prescription}")
    return "\n".join(sections) if sections else None


def get_line_items(db: Session, invoice_id: uuid.UUID) -> list[InvoiceLineItem]:
    stmt = select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice_id)
    return list(db.execute(stmt).scalars().all())


def common_line_items(db: Session) -> list[CommonLineItem]:
    stmt = select(
        InvoiceLineItem.description,
        InvoiceLineItem.unit_price_cents,
        func.count().label("price_count"),
    ).group_by(InvoiceLineItem.description, InvoiceLineItem.unit_price_cents)
    rows = db.execute(stmt).all()

    description_totals: dict[str, int] = {}
    best_price: dict[str, tuple[int, int]] = {}  # description -> (unit_price_cents, count)
    for description, unit_price_cents, price_count in rows:
        description_totals[description] = description_totals.get(description, 0) + price_count
        current = best_price.get(description)
        if current is None or price_count > current[1]:
            best_price[description] = (unit_price_cents, price_count)

    ranked = sorted(description_totals.items(), key=lambda item: item[1], reverse=True)
    return [
        CommonLineItem(description=description, unit_price_cents=best_price[description][0])
        for description, _ in ranked[:8]
    ]


def auto_draft_line_items(db: Session, invoice: Invoice, appointment: Appointment) -> None:
    """Best-effort: keep line items in sync with the appointment's vet notes.

    Re-drafts whenever the notes text differs from what was last synced (covers
    both the first draft and the vet adding/editing notes after the fact), and
    skips any drafted item whose description already exists on the invoice so a
    re-sync doesn't duplicate items that are already there. Never raises - AI
    drafting being unavailable (missing API key, LLM error, etc.) must not block
    invoice creation or block viewing the invoice; staff can always add line
    items by hand.
    """
    notes = appointment_notes_text(appointment)
    if notes is None or notes == invoice.synced_vet_notes:
        return
    try:
        catalog = common_line_items(db)
        items = draft_line_items(notes, catalog)
    except Exception:
        logger.exception("AI line-item drafting failed for invoice %s", invoice.id)
        return

    existing_descriptions = {item.description.strip().lower() for item in get_line_items(db, invoice.id)}
    for item in items:
        if item.description.strip().lower() in existing_descriptions:
            continue
        db.add(InvoiceLineItem(invoice_id=invoice.id, **item.model_dump()))
    invoice.synced_vet_notes = notes
    db.flush()
