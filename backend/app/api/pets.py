from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.tenancy import scoped
from app.db.session import get_db
from app.models.pet import Pet
from app.models.user import User
from app.schemas.pet import PetOut

router = APIRouter()


@router.get("", response_model=list[PetOut])
def list_pets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Pet]:
    stmt = scoped(select(Pet), Pet, current_user.clinic_id).order_by(Pet.name)
    return list(db.execute(stmt).scalars().all())
