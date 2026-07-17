import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPKMixin


class ReminderChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"


class ReminderStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Reminder(Base, UUIDPKMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "reminders"

    appointment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("appointments.id"), nullable=False, index=True)
    channel: Mapped[ReminderChannel] = mapped_column(
        Enum(
            ReminderChannel,
            name="reminder_channel",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
    )
    send_at: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[ReminderStatus] = mapped_column(
        Enum(
            ReminderStatus,
            name="reminder_status",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=ReminderStatus.PENDING,
        server_default=ReminderStatus.PENDING.value,
    )
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
