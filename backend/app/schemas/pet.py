import uuid
from datetime import date

from pydantic import BaseModel


class PetCreate(BaseModel):
    name: str
    species: str
    breed: str | None = None
    date_of_birth: date | None = None


class PetUpdate(BaseModel):
    name: str | None = None
    species: str | None = None
    breed: str | None = None
    date_of_birth: date | None = None


class PetOut(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    species: str
    breed: str | None
    date_of_birth: date | None

    model_config = {"from_attributes": True}
