import enum

from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPKMixin


class UserRole(str, enum.Enum):
    VET = "vet"
    TECH = "tech"
    FRONT_DESK = "front_desk"
    ADMIN = "admin"


class User(Base, UUIDPKMixin, TimestampMixin, TenantScopedMixin):
    """Clinic staff member."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    full_name: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
