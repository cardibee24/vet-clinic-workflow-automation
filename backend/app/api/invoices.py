import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.tenancy import scoped
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
)

router = APIRouter()

# Legal next states per current status; empty set means terminal.
_ALLOWED_TRANSITIONS: dict[InvoiceStatus, set[InvoiceStatus]] = {
    InvoiceStatus.DRAFT: {InvoiceStatus.ISSUED, InvoiceStatus.VOID},
    InvoiceStatus.ISSUED: {InvoiceStatus.PAID, InvoiceStatus.VOID},
    InvoiceStatus.PAID: set(),
    InvoiceStatus.VOID: set(),
}


def _get_invoice_or_404(db: Session, invoice_id: uuid.UUID, clinic_id: uuid.UUID) -> Invoice:
    stmt = scoped(select(Invoice).where(Invoice.id == invoice_id), Invoice, clinic_id)
    invoice = db.execute(stmt).scalar_one_or_none()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")
    return invoice


def _require_owner(db: Session, owner_id: uuid.UUID, clinic_id: uuid.UUID) -> Owner:
    stmt = scoped(select(Owner).where(Owner.id == owner_id), Owner, clinic_id)
    owner = db.execute(stmt).scalar_one_or_none()
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found")
    return owner


def _require_appointment_for_owner(
    db: Session, appointment_id: uuid.UUID, owner_id: uuid.UUID, clinic_id: uuid.UUID
) -> Appointment:
    stmt = scoped(select(Appointment).where(Appointment.id == appointment_id), Appointment, clinic_id)
    appointment = db.execute(stmt).scalar_one_or_none()
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    pet_stmt = scoped(select(Pet).where(Pet.id == appointment.pet_id), Pet, clinic_id)
    pet = db.execute(pet_stmt).scalar_one_or_none()
    if pet is None or pet.owner_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Appointment does not belong to this owner",
        )
    return appointment


def _get_line_items(db: Session, invoice_id: uuid.UUID, clinic_id: uuid.UUID) -> list[InvoiceLineItem]:
    stmt = scoped(
        select(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice_id), InvoiceLineItem, clinic_id
    )
    return list(db.execute(stmt).scalars().all())


@router.post("", response_model=InvoiceOut, status_code=status.HTTP_201_CREATED)
def create_invoice(
    body: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Invoice:
    _require_owner(db, body.owner_id, current_user.clinic_id)
    if body.appointment_id is not None:
        _require_appointment_for_owner(db, body.appointment_id, body.owner_id, current_user.clinic_id)

    invoice = Invoice(clinic_id=current_user.clinic_id, **body.model_dump())
    db.add(invoice)
    db.flush()
    return invoice


@router.get("", response_model=list[InvoiceOut])
def list_invoices(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Invoice]:
    stmt = scoped(select(Invoice), Invoice, current_user.clinic_id).order_by(Invoice.created_at.desc())
    return list(db.execute(stmt).scalars().all())


@router.get("/{invoice_id}", response_model=InvoiceWithLineItems)
def get_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvoiceWithLineItems:
    invoice = _get_invoice_or_404(db, invoice_id, current_user.clinic_id)
    line_items = _get_line_items(db, invoice.id, current_user.clinic_id)
    return InvoiceWithLineItems(line_items=list(line_items), **InvoiceOut.model_validate(invoice).model_dump())


@router.post("/{invoice_id}/line-items", response_model=LineItemOut, status_code=status.HTTP_201_CREATED)
def add_line_item(
    invoice_id: uuid.UUID,
    body: LineItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InvoiceLineItem:
    invoice = _get_invoice_or_404(db, invoice_id, current_user.clinic_id)
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot modify line items on a non-draft invoice",
        )

    line_item = InvoiceLineItem(clinic_id=current_user.clinic_id, invoice_id=invoice.id, **body.model_dump())
    db.add(line_item)
    db.flush()
    return line_item


@router.patch("/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(
    invoice_id: uuid.UUID,
    body: InvoiceStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Invoice:
    invoice = _get_invoice_or_404(db, invoice_id, current_user.clinic_id)
    if body.status not in _ALLOWED_TRANSITIONS[invoice.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition invoice from '{invoice.status.value}' to '{body.status.value}'",
        )

    if body.status == InvoiceStatus.ISSUED:
        line_items = _get_line_items(db, invoice.id, current_user.clinic_id)
        if not line_items:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Cannot issue an invoice with no line items",
            )
        invoice.issued_at = datetime.now(UTC).replace(tzinfo=None)

    invoice.status = body.status
    db.flush()
    return invoice
