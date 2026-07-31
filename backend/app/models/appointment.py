import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TimestampMixin, UUIDPKMixin


class AppointmentStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    CHECKED_IN = "checked_in"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class AppointmentReason(str, enum.Enum):
    CHECKUP = "checkup"
    VACCINATION = "vaccination"
    SURGERY = "surgery"
    DENTAL = "dental"
    FOLLOW_UP = "follow_up"
    EMERGENCY = "emergency"
    DIAGNOSTIC = "diagnostic"


class Appointment(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "appointments"

    pet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pets.id"), nullable=False, index=True)
    assigned_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[AppointmentStatus] = mapped_column(
        Enum(
            AppointmentStatus,
            name="appointment_status",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=AppointmentStatus.SCHEDULED,
        server_default=AppointmentStatus.SCHEDULED.value,
    )
    reason: Mapped[AppointmentReason | None] = mapped_column(
        Enum(
            AppointmentReason,
            name="appointment_reason",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=True,
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Short per-day queue ticket (e.g. "Q-042"), assigned at check-in - lets a client
    # look up their status by typing a few digits instead of pasting a UUID. Resets
    # each day (see _assign_ticket_number in api/appointments.py), so it's only
    # meaningful together with checked_in_at's date, not unique on its own.
    ticket_number: Mapped[int | None] = mapped_column(nullable=True)
    visit_notes: Mapped[str | None] = mapped_column(nullable=True)
    prescription: Mapped[str | None] = mapped_column(nullable=True)
