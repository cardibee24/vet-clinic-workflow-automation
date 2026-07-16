import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.core.tenancy import scoped
from app.db.session import get_db
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the logged-in user (and their clinic) from the bearer token.

    clinic_id comes from the signed JWT claim set at login (app/api/auth.py),
    never from a client-supplied field, and the lookup below is still run
    through scoped() per the tenancy convention (app/core/tenancy.py) so a
    forged/mismatched clinic_id in a tampered token simply matches no row
    instead of leaking another clinic's user.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
        clinic_id = uuid.UUID(payload["clinic_id"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise unauthorized

    stmt = scoped(select(User).where(User.id == user_id), User, clinic_id)
    user = db.execute(stmt).scalar_one_or_none()
    if user is None or not user.is_active:
        raise unauthorized

    return user
