import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPKMixin


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Appointment(Base, UUIDPKMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "appointments"

    pet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pets.id"), nullable=False, index=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    scheduled_start: Mapped[datetime] = mapped_column(nullable=False)
    scheduled_end: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(AppointmentStatus, name="appointment_status"),
        nullable=False,
        default=AppointmentStatus.SCHEDULED,
        server_default=AppointmentStatus.SCHEDULED.value,
    )
    reason: Mapped[str | None] = mapped_column(nullable=True)
