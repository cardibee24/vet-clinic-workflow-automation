import uuid

from pydantic import BaseModel

from app.schemas.pet import PetOut


class OwnerCreate(BaseModel):
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None


class OwnerUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None


class OwnerOut(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str | None
    phone: str | None

    model_config = {"from_attributes": True}


class OwnerWithPets(OwnerOut):
    pets: list[PetOut] = []


class PublicPetSummary(BaseModel):
    id: uuid.UUID
    name: str
    species: str


class PublicOwnerLookupResult(BaseModel):
    """Minimal, non-sensitive projection returned by the public phone lookup.

    Deliberately omits email/phone/etc. - the caller already knows their own
    contact details, so there's no reason to echo them back to an
    unauthenticated request.
    """

    owner_id: uuid.UUID
    first_name: str
    last_name: str
    pets: list[PublicPetSummary]
