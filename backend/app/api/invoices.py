import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai.invoice_draft import draft_line_items
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.invoice import Invoice, InvoiceLineItem, InvoiceStatus
from app.models.owner import Owner
from app.models.pet import Pet
from app.models.user import User
from app.schemas.invoice import (
    CommonLineItem,
    DraftLineItemsRequest,
    InvoiceCreate,
    InvoiceListOut,
    InvoiceOut,
    InvoiceStatusUpdate,
    InvoiceWithLineItems,
    LineItemCreate,
    LineItemOut,
    LineItemUpdate,
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Legal next states per current status; empty set means terminal.
_ALLOWED_TRANSITIONS: dict[InvoiceStatus, set[InvoiceStatus]] = {
    InvoiceStatus.DRAFT: {InvoiceStatus.ISSUED, InvoiceStatus.VOID},
    InvoiceStatus.ISSUED: {InvoiceStatus.PAID, InvoiceStatus.VOID},
    InvoiceStatus.PAID: set(),
    InvoiceStatus.VOID: set(),
}


def _get_invoice_or_404(db: Session, invoice_id: uuid.UUID) -> Invoice:
    invoice = db.execute(select(Invoice).where(Invoice.id == invoice_id)).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def _require_owner(db: Session, owner_id: uuid.UUID) -> Owner:
    owner = db.execute(select(Owner).where(Owner.id == owner_id)).scalar_one_or_none()
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found")
    return owner


def _require_appointment_for_owner(db: Session, appointment_id: uuid.UUID, owner_id: uuid.UUID) -> Appointment:
    appointment = db.execute(select(Appointment).where(Appointment.id == appointment_id)).scalar_one_or_none()
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    pet = db.execute(select(Pet).where(Pet.id == appointment.pet_id)).scalar_one_or_none()
    if pet is None or pet.owner_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Appointment does not belong to this owner",
        )
    return appointment


def _appointment_notes_text(appointment: Appointment) -> str | None:
    sections = []
    if appointment.visit_notes:
        sections.append(f"Description: {appointment.visit_notes}")
    if appointment.prescription:
        sections.append(f"Prescription: {appointment.prescription}")
    return "\n".join(sections) if sections else None


def _auto_draft_line_items(db: Session, invoice: Invoice, appointment: Appointment) -> None:
    """Best-effort: keep line items in sync with the appointment's vet notes.

    Re-drafts whenever the notes text differs from what was last synced (covers
    both the first draft and the vet adding/editing notes after the fact), and
    skips any drafted item whose description already exists on the invoice so a
    re-sync doesn't duplicate items that are already there. Never raises - AI
    drafting being unavailable (missing API key, LLM error, etc.) must not block
    invoice creation or block viewing the invoice; staff can always add line
    items by hand.
    """
    notes = _appointment_notes_text(appointment)
    if notes is None or notes == invoice.synced_vet_notes:
        return
    try:
        catalog = _common_line_items(db)
        items = draft_line_items(notes, catalog)
    except Exception:
        logger.exception("AI line-item drafting failed for invoice %s", invoice.id)
        return

    existing_descriptions = {item.description.strip().lower() for item in _get_line_items(db, invoice.id)}
    for item in items:
        if item.description.strip().lower() in existing_descriptions:
            continue
        db.add(InvoiceLineItem(invoice_id=invoice.id, **item.model_dump()))
    invoice.synced_vet_notes = notes
    db.flush()


def _get_line_items(db: Session, invoice_id: uuid.UUID) -> list[InvoiceLineItem]:
    stmt = select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice_id)
    return list(db.execute(stmt).scalars().all())


def _get_line_item_or_404(db: Session, invoice_id: uuid.UUID, line_item_id: uuid.UUID) -> InvoiceLineItem:
    stmt = select(InvoiceLineItem).where(
        InvoiceLineItem.id == line_item_id, InvoiceLineItem.invoice_id == invoice_id
    )
    line_item = db.execute(stmt).scalar_one_or_none()
    if line_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line item not found")
    return line_item


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(
    body: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Invoice:
    _require_owner(db, body.owner_id)
    appointment = None
    if body.appointment_id is not None:
        appointment = _require_appointment_for_owner(db, body.appointment_id, body.owner_id)

    invoice = Invoice(**body.model_dump())
    db.add(invoice)
    db.flush()

    if appointment is not None:
        _auto_draft_line_items(db, invoice, appointment)

    return invoice


@router.get("", response_model=list[InvoiceListOut])
def list_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InvoiceListOut]:
    stmt = select(Invoice).order_by(Invoice.created_at.desc())
    invoices = list(db.execute(stmt).scalars().all())

    totals_stmt = select(
        InvoiceLineItem.invoice_id,
        func.sum(InvoiceLineItem.quantity * InvoiceLineItem.unit_price_cents),
    ).group_by(InvoiceLineItem.invoice_id)
    totals = dict(db.execute(totals_stmt).all())

    return [
        InvoiceListOut(**InvoiceOut.model_validate(invoice).model_dump(), total_cents=int(totals.get(invoice.id, 0)))
        for invoice in invoices
    ]


def _common_line_items(db: Session) -> list[CommonLineItem]:
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


@router.get("/common-line-items", response_model=list[CommonLineItem])
def get_common_line_items(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CommonLineItem]:
    """Most frequently used line-item descriptions, with their most commonly charged price, for quick-add."""
    return _common_line_items(db)


@router.post("/draft-line-items", response_model=list[LineItemCreate])
def draft_line_items_endpoint(
    body: DraftLineItemsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[LineItemCreate]:
    """Propose invoice line items from free-text visit notes using an LLM.

    Nothing is saved here — review the proposals and add each one via the
    existing add-line-item endpoint.
    """
    catalog = _common_line_items(db)
    try:
        return draft_line_items(body.notes, catalog)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI drafting is unavailable right now. Check GOOGLE_API_KEY and try again.",
        ) from exc


@router.get("/{invoice_id}", response_model=InvoiceWithLineItems)
def get_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvoiceWithLineItems:
    invoice = _get_invoice_or_404(db, invoice_id)
    line_items = _get_line_items(db, invoice.id)
    return InvoiceWithLineItems(line_items=list(line_items), **InvoiceOut.model_validate(invoice).model_dump())


@router.post("/{invoice_id}/auto-draft-line-items", response_model=InvoiceWithLineItems)
def retry_auto_draft_line_items(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvoiceWithLineItems:
    """Sync line items with the linked appointment's current vet notes.

    Covers invoices created before notes were written, AI drafting being
    unavailable at creation time (e.g. GOOGLE_API_KEY wasn't set yet), and the
    vet adding or editing notes after the invoice already has line items. A
    no-op if the invoice isn't a draft, has no linked appointment, has no
    notes, or the notes haven't changed since the last sync.
    """
    invoice = _get_invoice_or_404(db, invoice_id)
    if invoice.status == InvoiceStatus.DRAFT and invoice.appointment_id is not None:
        appointment = db.execute(
            select(Appointment).where(Appointment.id == invoice.appointment_id)
        ).scalar_one_or_none()
        if appointment is not None:
            _auto_draft_line_items(db, invoice, appointment)

    line_items = _get_line_items(db, invoice.id)
    return InvoiceWithLineItems(line_items=list(line_items), **InvoiceOut.model_validate(invoice).model_dump())


@router.post("/{invoice_id}/line-items", response_model=LineItemOut, status_code=status.HTTP_201_CREATED)
def add_line_item(
    invoice_id: uuid.UUID,
    body: LineItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvoiceLineItem:
    invoice = _get_invoice_or_404(db, invoice_id)
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot modify line items on a non-draft invoice",
        )

    line_item = InvoiceLineItem(invoice_id=invoice.id, **body.model_dump())
    db.add(line_item)
    db.flush()
    return line_item


@router.patch("/{invoice_id}/line-items/{line_item_id}", response_model=LineItemOut)
def update_line_item(
    invoice_id: uuid.UUID,
    line_item_id: uuid.UUID,
    body: LineItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvoiceLineItem:
    invoice = _get_invoice_or_404(db, invoice_id)
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot modify line items on a non-draft invoice",
        )

    line_item = _get_line_item_or_404(db, invoice_id, line_item_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(line_item, field, value)
    db.flush()
    return line_item


@router.delete("/{invoice_id}/line-items/{line_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_line_item(
    invoice_id: uuid.UUID,
    line_item_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    invoice = _get_invoice_or_404(db, invoice_id)
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot modify line items on a non-draft invoice",
        )

    line_item = _get_line_item_or_404(db, invoice_id, line_item_id)
    db.delete(line_item)
    db.flush()


@router.patch("/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(
    invoice_id: uuid.UUID,
    body: InvoiceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Invoice:
    invoice = _get_invoice_or_404(db, invoice_id)
    if body.status not in _ALLOWED_TRANSITIONS[invoice.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition invoice from '{invoice.status.value}' to '{body.status.value}'",
        )

    if body.status == InvoiceStatus.ISSUED:
        line_items = _get_line_items(db, invoice.id)
        if not line_items:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Cannot issue an invoice with no line items",
            )
        invoice.issued_at = datetime.now(UTC).replace(tzinfo=None)

    if body.status == InvoiceStatus.PAID:
        if body.payment_method is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="payment_method is required when marking an invoice as paid",
            )
        invoice.payment_method = body.payment_method
        invoice.paid_at = datetime.now(UTC).replace(tzinfo=None)

    invoice.status = body.status
    db.flush()
    return invoice


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    invoice = _get_invoice_or_404(db, invoice_id)

    for line_item in _get_line_items(db, invoice.id):
        db.delete(line_item)
    db.flush()

    db.delete(invoice)
    db.flush()
