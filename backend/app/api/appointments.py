import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.invoice import Invoice, InvoiceStatus
from app.models.pet import Pet
from app.models.user import User
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentNotesUpdate,
    AppointmentOut,
    AppointmentQueueStatus,
    AppointmentStatusUpdate,
    AppointmentUpdate,
    QueueEntry,
    QueueSummary,
    SelfCheckInRequest,
)
from app.schemas.invoice import InvoiceOut
from app.services.invoice_drafting import appointment_notes_text, auto_draft_line_items

router = APIRouter()

# Legal next states per current status; empty set means terminal.
_ALLOWED_TRANSITIONS: dict[AppointmentStatus, set[AppointmentStatus]] = {
    AppointmentStatus.SCHEDULED: {
        AppointmentStatus.CHECKED_IN,
        AppointmentStatus.CANCELLED,
        AppointmentStatus.NO_SHOW,
    },
    AppointmentStatus.CHECKED_IN: {AppointmentStatus.IN_PROGRESS, AppointmentStatus.CANCELLED},
    AppointmentStatus.IN_PROGRESS: {AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED},
    AppointmentStatus.COMPLETED: set(),
    AppointmentStatus.CANCELLED: set(),
    AppointmentStatus.NO_SHOW: set(),
}

_TERMINAL_STATUSES = {status_ for status_, next_states in _ALLOWED_TRANSITIONS.items() if not next_states}


def _get_appointment_or_404(db: Session, appointment_id: uuid.UUID) -> Appointment:
    appointment = db.execute(select(Appointment).where(Appointment.id == appointment_id)).scalar_one_or_none()
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


def _require_pet(db: Session, pet_id: uuid.UUID) -> Pet:
    pet = db.execute(select(Pet).where(Pet.id == pet_id)).scalar_one_or_none()
    if pet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
    return pet


def _require_assigned_user(db: Session, user_id: uuid.UUID) -> User:
    assigned = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if assigned is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found")
    return assigned


def _get_waiting_appointments(db: Session) -> list[Appointment]:
    """Checked-in appointments not yet in progress, oldest check-in first."""
    stmt = (
        select(Appointment)
        .where(Appointment.status == AppointmentStatus.CHECKED_IN)
        .order_by(Appointment.checked_in_at)
    )
    return list(db.execute(stmt).scalars().all())


def _today_start() -> datetime:
    now = datetime.now(UTC).replace(tzinfo=None)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def _get_or_create_invoice_for_appointment(db: Session, appointment: Appointment) -> Invoice:
    """The invoice this appointment bills to, creating one (as a draft) on first
    use so saving vet notes is what starts the billing paper trail - staff
    shouldn't have to separately remember to go create an invoice."""
    existing = db.execute(select(Invoice).where(Invoice.appointment_id == appointment.id)).scalars().first()
    if existing is not None:
        return existing

    pet = db.execute(select(Pet).where(Pet.id == appointment.pet_id)).scalar_one()
    invoice = Invoice(owner_id=pet.owner_id, appointment_id=appointment.id)
    db.add(invoice)
    db.flush()
    return invoice


def _assign_ticket_number(db: Session) -> int:
    """Next short ticket number for today's queue (e.g. displayed as "Q-042").

    Resets daily - only the highest ticket_number among today's check-ins matters,
    so re-run this at every check-in rather than using a global counter/sequence.
    """
    stmt = select(func.max(Appointment.ticket_number)).where(Appointment.checked_in_at >= _today_start())
    highest = db.execute(stmt).scalar_one_or_none()
    return (highest or 0) + 1


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_appointment(
    body: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Appointment:
    _require_pet(db, body.pet_id)
    if body.assigned_user_id is not None:
        _require_assigned_user(db, body.assigned_user_id)

    appointment = Appointment(**body.model_dump())
    db.add(appointment)
    db.flush()
    return appointment


@router.post("/self-check-in", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def self_check_in(
    body: SelfCheckInRequest,
    db: Session = Depends(get_db),
) -> Appointment:
    """Public: lets a client check themselves in for a walk-in, no login required.

    Creates the appointment already checked in, scheduled for right now -
    there is no prior booking to attach to.
    """
    _require_pet(db, body.pet_id)

    appointment = Appointment(
        pet_id=body.pet_id,
        reason=body.reason,
        scheduled_at=datetime.now(UTC).replace(tzinfo=None),
        status=AppointmentStatus.CHECKED_IN,
        checked_in_at=datetime.now(UTC).replace(tzinfo=None),
    )
    appointment.ticket_number = _assign_ticket_number(db)
    db.add(appointment)
    db.flush()
    return appointment


@router.get("", response_model=list[AppointmentOut])
def list_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Appointment]:
    stmt = select(Appointment).order_by(Appointment.scheduled_at)
    return list(db.execute(stmt).scalars().all())


@router.get("/queue", response_model=QueueSummary)
def get_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> QueueSummary:
    waiting = _get_waiting_appointments(db)
    entries = [
        QueueEntry(
            position=index + 1,
            appointment_id=appointment.id,
            pet_id=appointment.pet_id,
            checked_in_at=appointment.checked_in_at,
            ticket_number=appointment.ticket_number,
            reason=appointment.reason,
        )
        for index, appointment in enumerate(waiting)
    ]
    return QueueSummary(total_waiting=len(entries), entries=entries)


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Appointment:
    return _get_appointment_or_404(db, appointment_id)


@router.get("/{appointment_id}/queue", response_model=AppointmentQueueStatus)
def get_appointment_queue_status(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> AppointmentQueueStatus:
    """Public: lets a client check their own queue position by appointment ID, no login required."""
    appointment = db.execute(select(Appointment).where(Appointment.id == appointment_id)).scalar_one_or_none()
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    waiting = _get_waiting_appointments(db)
    position = next((i + 1 for i, a in enumerate(waiting) if a.id == appointment.id), None)
    return AppointmentQueueStatus(
        appointment_id=appointment.id,
        status=appointment.status,
        ticket_number=appointment.ticket_number,
        position=position,
        total_waiting=len(waiting),
    )


@router.get("/ticket/{ticket_number}", response_model=AppointmentQueueStatus)
def get_queue_status_by_ticket(
    ticket_number: int,
    db: Session = Depends(get_db),
) -> AppointmentQueueStatus:
    """Public: lets a client check their status with today's short ticket number
    (e.g. "042") instead of pasting the full appointment ID - easier to type on a
    phone. Ticket numbers reset daily, so this only searches today's check-ins."""
    appointment = db.execute(
        select(Appointment).where(
            Appointment.ticket_number == ticket_number,
            Appointment.checked_in_at >= _today_start(),
        )
    ).scalar_one_or_none()
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No appointment found for that ticket number today")

    waiting = _get_waiting_appointments(db)
    position = next((i + 1 for i, a in enumerate(waiting) if a.id == appointment.id), None)
    return AppointmentQueueStatus(
        appointment_id=appointment.id,
        status=appointment.status,
        ticket_number=appointment.ticket_number,
        position=position,
        total_waiting=len(waiting),
    )


@router.patch("/{appointment_id}", response_model=AppointmentOut)
def update_appointment(
    appointment_id: uuid.UUID,
    body: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Appointment:
    appointment = _get_appointment_or_404(db, appointment_id)
    if appointment.status in _TERMINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot edit an appointment that is '{appointment.status.value}'",
        )

    updates = body.model_dump(exclude_unset=True)
    if "assigned_user_id" in updates and updates["assigned_user_id"] is not None:
        _require_assigned_user(db, updates["assigned_user_id"])

    for field, value in updates.items():
        setattr(appointment, field, value)
    db.flush()
    return appointment


@router.patch("/{appointment_id}/notes", response_model=AppointmentOut)
def update_appointment_notes(
    appointment_id: uuid.UUID,
    body: AppointmentNotesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Appointment:
    """Visit notes are clinical documentation, not scheduling metadata - editable regardless of status.

    Saving notes is also what starts billing for the visit: as soon as there's
    something to describe, get-or-create the invoice for this appointment and
    (re)draft its line items from the notes, rather than waiting for a
    separate "create invoice" step.
    """
    appointment = _get_appointment_or_404(db, appointment_id)
    appointment.visit_notes = body.visit_notes
    appointment.prescription = body.prescription
    db.flush()

    if appointment_notes_text(appointment) is not None:
        invoice = _get_or_create_invoice_for_appointment(db, appointment)
        if invoice.status == InvoiceStatus.DRAFT:
            auto_draft_line_items(db, invoice, appointment)

    return appointment


@router.get("/{appointment_id}/invoice", response_model=InvoiceOut)
def get_appointment_invoice(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Invoice:
    """The invoice already created for this appointment (via saving vet notes), if any."""
    _get_appointment_or_404(db, appointment_id)
    invoice = db.execute(select(Invoice).where(Invoice.appointment_id == appointment_id)).scalars().first()
    if invoice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No invoice for this appointment yet")
    return invoice


@router.patch("/{appointment_id}/status", response_model=AppointmentOut)
def update_appointment_status(
    appointment_id: uuid.UUID,
    body: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Appointment:
    appointment = _get_appointment_or_404(db, appointment_id)
    if body.status not in _ALLOWED_TRANSITIONS[appointment.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition appointment from '{appointment.status.value}' to '{body.status.value}'",
        )
    if body.status == AppointmentStatus.CHECKED_IN:
        appointment.checked_in_at = datetime.now(UTC).replace(tzinfo=None)
        appointment.ticket_number = _assign_ticket_number(db)
    appointment.status = body.status
    db.flush()
    return appointment


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    appointment = _get_appointment_or_404(db, appointment_id)

    has_invoices = (
        db.execute(select(Invoice.id).where(Invoice.appointment_id == appointment.id).limit(1)).first()
        is not None
    )
    if has_invoices:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete an appointment with existing invoices",
        )

    db.delete(appointment)
    db.flush()
