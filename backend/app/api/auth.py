from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, Token, UserOut

router = APIRouter()


@router.post("/login", response_model=Token)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> Token:
    user = db.execute(select(User).where(User.email == body.email)).scalar_one_or_none()

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect email or password",
    )
    if user is None or not user.is_active:
        raise invalid_credentials
    if not verify_password(body.password, user.hashed_password):
        raise invalid_credentials

    access_token = create_access_token(user_id=user.id)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserOut)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user
