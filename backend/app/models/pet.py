import uuid
from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPKMixin


class Pet(Base, UUIDPKMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "pets"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("owners.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(nullable=False)
    species: Mapped[str] = mapped_column(nullable=False)
    breed: Mapped[str | None] = mapped_column(nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(nullable=True)
