import uuid

from pydantic import BaseModel

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}
