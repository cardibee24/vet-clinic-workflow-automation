import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.appointment import AppointmentStatus


class AppointmentCreate(BaseModel):
    pet_id: uuid.UUID
    assigned_user_id: uuid.UUID | None = None
    scheduled_at: datetime
    reason: str | None = None


class AppointmentOut(BaseModel):
    id: uuid.UUID
    pet_id: uuid.UUID
    assigned_user_id: uuid.UUID | None
    scheduled_at: datetime
    status: AppointmentStatus
    reason: str | None
    checked_in_at: datetime | None

    model_config = {"from_attributes": True}


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


class QueueEntry(BaseModel):
    position: int
    appointment_id: uuid.UUID
    pet_id: uuid.UUID
    checked_in_at: datetime | None
    reason: str | None


class QueueSummary(BaseModel):
    total_waiting: int
    entries: list[QueueEntry]


class AppointmentQueueStatus(BaseModel):
    appointment_id: uuid.UUID
    status: AppointmentStatus
    position: int | None
    total_waiting: int
