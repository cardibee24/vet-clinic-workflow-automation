import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.invoice import Invoice, InvoiceLineItem, InvoiceStatus
from app.models.owner import Owner
from app.models.pet import Pet
from app.models.user import User
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceOut,
    InvoiceStatusUpdate,
    InvoiceWithLineItems,
    LineItemCreate,
    LineItemOut,
    LineItemUpdate,
)

router = APIRouter()

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
    if body.appointment_id is not None:
        _require_appointment_for_owner(db, body.appointment_id, body.owner_id)

    invoice = Invoice(**body.model_dump())
    db.add(invoice)
    db.flush()
    return invoice


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Invoice]:
    stmt = select(Invoice).order_by(Invoice.created_at.desc())
    return list(db.execute(stmt).scalars().all())


@router.get("/{invoice_id}", response_model=InvoiceWithLineItems)
def get_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvoiceWithLineItems:
    invoice = _get_invoice_or_404(db, invoice_id)
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
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a non-draft invoice; void it instead",
        )

    for line_item in _get_line_items(db, invoice.id):
        db.delete(line_item)
    db.flush()

    db.delete(invoice)
    db.flush()
