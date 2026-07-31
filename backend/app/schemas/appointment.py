import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.appointment import AppointmentReason, AppointmentStatus


class AppointmentCreate(BaseModel):
    pet_id: uuid.UUID
    assigned_user_id: uuid.UUID | None = None
    scheduled_at: datetime
    reason: AppointmentReason | None = None


class AppointmentOut(BaseModel):
    id: uuid.UUID
    pet_id: uuid.UUID
    assigned_user_id: uuid.UUID | None
    scheduled_at: datetime
    status: AppointmentStatus
    reason: AppointmentReason | None
    checked_in_at: datetime | None
    ticket_number: int | None
    visit_notes: str | None
    prescription: str | None

    model_config = {"from_attributes": True}


class AppointmentUpdate(BaseModel):
    scheduled_at: datetime | None = None
    reason: AppointmentReason | None = None
    assigned_user_id: uuid.UUID | None = None


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus


class AppointmentNotesUpdate(BaseModel):
    visit_notes: str | None = None
    prescription: str | None = None


class SelfCheckInRequest(BaseModel):
    pet_id: uuid.UUID
    reason: AppointmentReason | None = None


class QueueEntry(BaseModel):
    position: int
    appointment_id: uuid.UUID
    pet_id: uuid.UUID
    checked_in_at: datetime | None
    ticket_number: int | None
    reason: AppointmentReason | None


class QueueSummary(BaseModel):
    total_waiting: int
    entries: list[QueueEntry]


class AppointmentQueueStatus(BaseModel):
    appointment_id: uuid.UUID
    status: AppointmentStatus
    ticket_number: int | None
    position: int | None
    total_waiting: int
