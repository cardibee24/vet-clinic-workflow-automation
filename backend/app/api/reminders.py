import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.tenancy import scoped
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.reminder import Reminder, ReminderStatus
from app.models.user import User
from app.schemas.reminder import ReminderCreate, ReminderOut, ReminderStatusUpdate

router = APIRouter()

# Legal next states per current status; empty set means terminal.
_ALLOWED_TRANSITIONS: dict[ReminderStatus, set[ReminderStatus]] = {
    ReminderStatus.PENDING: {ReminderStatus.SENT, ReminderStatus.FAILED, ReminderStatus.CANCELLED},
    ReminderStatus.FAILED: {ReminderStatus.PENDING, ReminderStatus.CANCELLED},
    ReminderStatus.SENT: set(),
    ReminderStatus.CANCELLED: set(),
}


def _get_reminder_or_404(db: Session, reminder_id: uuid.UUID, clinic_id: uuid.UUID) -> Reminder:
    stmt = scoped(select(Reminder).where(Reminder.id == reminder_id), Reminder, clinic_id)
    reminder = db.execute(stmt).scalar_one_or_none()
    if reminder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reminder not found")
    return reminder


def _require_appointment(db: Session, appointment_id: uuid.UUID, clinic_id: uuid.UUID) -> Appointment:
    stmt = scoped(select(Appointment).where(Appointment.id == appointment_id), Appointment, clinic_id)
    appointment = db.execute(stmt).scalar_one_or_none()
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


@router.post("", response_model=ReminderOut, status_code=status.HTTP_201_CREATED)
def create_reminder(
    body: ReminderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Reminder:
    appointment = _require_appointment(db, body.appointment_id, current_user.clinic_id)
    if body.send_at >= appointment.scheduled_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="send_at must be before the appointment's scheduled_start",
        )

    reminder = Reminder(clinic_id=current_user.clinic_id, **body.model_dump())
    db.add(reminder)
    db.flush()
    return reminder


@router.get("", response_model=list[ReminderOut])
def list_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Reminder]:
    stmt = scoped(select(Reminder), Reminder, current_user.clinic_id).order_by(Reminder.send_at)
    return list(db.execute(stmt).scalars().all())


@router.get("/{reminder_id}", response_model=ReminderOut)
def get_reminder(
    reminder_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Reminder:
    return _get_reminder_or_404(db, reminder_id, current_user.clinic_id)


@router.patch("/{reminder_id}/status", response_model=ReminderOut)
def update_reminder_status(
    reminder_id: uuid.UUID,
    body: ReminderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Reminder:
    reminder = _get_reminder_or_404(db, reminder_id, current_user.clinic_id)
    if body.status not in _ALLOWED_TRANSITIONS[reminder.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition reminder from '{reminder.status.value}' to '{body.status.value}'",
        )
    reminder.status = body.status
    reminder.sent_at = datetime.now(UTC).replace(tzinfo=None) if body.status == ReminderStatus.SENT else reminder.sent_at
    db.flush()
    return reminder
