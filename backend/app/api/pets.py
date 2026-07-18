import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.pet import Pet
from app.models.user import User
from app.schemas.pet import PetOut, PetUpdate

router = APIRouter()


def _get_pet_or_404(db: Session, pet_id: uuid.UUID) -> Pet:
    pet = db.execute(select(Pet).where(Pet.id == pet_id)).scalar_one_or_none()
    if pet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pet not found")
    return pet


@router.get("", response_model=list[PetOut])
def list_pets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Pet]:
    stmt = select(Pet).order_by(Pet.name)
    return list(db.execute(stmt).scalars().all())


@router.patch("/{pet_id}", response_model=PetOut)
def update_pet(
    pet_id: uuid.UUID,
    body: PetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Pet:
    pet = _get_pet_or_404(db, pet_id)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(pet, field, value)
    db.flush()
    return pet


@router.delete("/{pet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pet(
    pet_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    pet = _get_pet_or_404(db, pet_id)

    has_appointments = (
        db.execute(select(Appointment.id).where(Appointment.pet_id == pet.id).limit(1)).first() is not None
    )
    if has_appointments:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete a pet with existing appointments",
        )

    db.delete(pet)
    db.flush()
