import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.tenancy import scoped
from app.db.session import get_db
from app.models.owner import Owner
from app.models.pet import Pet
from app.models.user import User
from app.schemas.owner import OwnerCreate, OwnerOut, OwnerWithPets
from app.schemas.pet import PetCreate, PetOut

router = APIRouter()


def _get_owner_or_404(db: Session, owner_id: uuid.UUID, clinic_id: uuid.UUID) -> Owner:
    stmt = scoped(select(Owner).where(Owner.id == owner_id), Owner, clinic_id)
    owner = db.execute(stmt).scalar_one_or_none()
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found")
    return owner


@router.post("", response_model=OwnerOut, status_code=status.HTTP_201_CREATED)
def create_owner(
    body: OwnerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Owner:
    owner = Owner(clinic_id=current_user.clinic_id, **body.model_dump())
    db.add(owner)
    db.flush()
    return owner


@router.get("", response_model=list[OwnerOut])
def list_owners(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Owner]:
    stmt = scoped(select(Owner), Owner, current_user.clinic_id).order_by(Owner.last_name, Owner.first_name)
    return list(db.execute(stmt).scalars().all())


@router.get("/{owner_id}", response_model=OwnerWithPets)
def get_owner(
    owner_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OwnerWithPets:
    owner = _get_owner_or_404(db, owner_id, current_user.clinic_id)
    pets_stmt = scoped(select(Pet).where(Pet.owner_id == owner.id), Pet, current_user.clinic_id)
    pets = db.execute(pets_stmt).scalars().all()
    return OwnerWithPets(pets=list(pets), **OwnerOut.model_validate(owner).model_dump())


@router.post("/{owner_id}/pets", response_model=PetOut, status_code=status.HTTP_201_CREATED)
def add_pet(
    owner_id: uuid.UUID,
    body: PetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Pet:
    owner = _get_owner_or_404(db, owner_id, current_user.clinic_id)
    pet = Pet(clinic_id=current_user.clinic_id, owner_id=owner.id, **body.model_dump())
    db.add(pet)
    db.flush()
    return pet
