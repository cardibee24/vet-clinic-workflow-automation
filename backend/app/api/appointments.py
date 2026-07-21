import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.invoice import Invoice
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
    """Visit notes are clinical documentation, not scheduling metadata - editable regardless of status."""
    appointment = _get_appointment_or_404(db, appointment_id)
    appointment.visit_notes = body.visit_notes
    appointment.prescription = body.prescription
    db.flush()
    return appointment


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
