from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class Clinic(Base, UUIDPKMixin, TimestampMixin):
    """The tenant root. Every other tenant-scoped table hangs off clinic_id."""

    __tablename__ = "clinics"

    name: Mapped[str] = mapped_column(nullable=False)
