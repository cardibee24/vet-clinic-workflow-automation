import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.tenancy import scoped
from app.db.session import get_db
from app.models.appointment import Appointment, AppointmentStatus
from app.models.pet import Pet
from app.models.user import User
from app.schemas.appointment import AppointmentCreate, AppointmentOut, AppointmentStatusUpdate

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


def _get_appointment_or_404(db: Session, appointment_id: uuid.UUID, clinic_id: uuid.UUID) -> Appointment:
    stmt = scoped(select(Appointment).where(Appointment.id == appointment_id), Appointment, clinic_id)
    appointment = db.execute(stmt).scalar_one_or_none()
    if appointment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appointment


def _require_pet(db: Session, pet_id: uuid.UUID, clinic_id: uuid.UUID) -> Pet:
    stmt = scoped(select(Pet).where(Pet.id == pet_id), Pet, clinic_id)
    pet = db.execute(stmt).scalar_one_or_none()
    if pet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
    return pet


def _require_assigned_user(db: Session, user_id: uuid.UUID, clinic_id: uuid.UUID) -> User:
    stmt = scoped(select(User).where(User.id == user_id), User, clinic_id)
    assigned = db.execute(stmt).scalar_one_or_none()
    if assigned is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assigned user not found")
    return assigned


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_appointment(
    body: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Appointment:
    _require_pet(db, body.pet_id, current_user.clinic_id)
    if body.assigned_user_id is not None:
        _require_assigned_user(db, body.assigned_user_id, current_user.clinic_id)

    appointment = Appointment(clinic_id=current_user.clinic_id, **body.model_dump())
    db.add(appointment)
    db.flush()
    return appointment


@router.get("", response_model=list[AppointmentOut])
def list_appointments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Appointment]:
    stmt = scoped(select(Appointment), Appointment, current_user.clinic_id).order_by(Appointment.scheduled_start)
    return list(db.execute(stmt).scalars().all())


@router.get("/{appointment_id}", response_model=AppointmentOut)
def get_appointment(
    appointment_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Appointment:
    return _get_appointment_or_404(db, appointment_id, current_user.clinic_id)


@router.patch("/{appointment_id}/status", response_model=AppointmentOut)
def update_appointment_status(
    appointment_id: uuid.UUID,
    body: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Appointment:
    appointment = _get_appointment_or_404(db, appointment_id, current_user.clinic_id)
    if body.status not in _ALLOWED_TRANSITIONS[appointment.status]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot transition appointment from '{appointment.status.value}' to '{body.status.value}'",
        )
    appointment.status = body.status
    db.flush()
    return appointment
