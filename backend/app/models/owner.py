from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Owner(Base, UUIDPKMixin, TimestampMixin):
    """A pet owner / client of a clinic."""

    __tablename__ = "owners"

    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=False)
    email: Mapped[str | None] = mapped_column(nullable=True)
    phone: Mapped[str | None] = mapped_column(nullable=True)
