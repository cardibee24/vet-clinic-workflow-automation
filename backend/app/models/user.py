import enum

from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class UserRole(str, enum.Enum):
    VET = "vet"
    # Clinic owner/manager staff role - unrelated to the Owner model (pet-owning clients).
    OWNER = "owner"


class User(Base, UUIDPKMixin, TimestampMixin):
    """Clinic staff member."""

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    full_name: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda enum_cls: [e.value for e in enum_cls]),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(default=True, server_default="true")
