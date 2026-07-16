import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings

settings = get_settings()

TOKEN_TYPE = "bearer"


def hash_password(plain_password: str) -> str:
    return bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(user_id: uuid.UUID, clinic_id: uuid.UUID) -> str:
    """Issue a JWT binding a user to the clinic they belong to.

    clinic_id is embedded here from the user's own row at login time (see
    app/api/auth.py), not supplied by the client - get_current_user (app/core/deps.py)
    later trusts this claim instead of re-deriving it, so this is the one place
    clinic_id enters the token.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "clinic_id": str(clinic_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
