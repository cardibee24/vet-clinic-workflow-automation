import uuid

from pydantic import BaseModel

from app.schemas.pet import PetOut


class OwnerCreate(BaseModel):
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None


class OwnerOut(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    first_name: str
    last_name: str
    email: str | None
    phone: str | None

    model_config = {"from_attributes": True}


class OwnerWithPets(OwnerOut):
    pets: list[PetOut] = []
