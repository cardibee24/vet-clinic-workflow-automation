import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.reminder import ReminderChannel, ReminderStatus


class ReminderCreate(BaseModel):
    appointment_id: uuid.UUID
    channel: ReminderChannel
    send_at: datetime


class ReminderOut(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    appointment_id: uuid.UUID
    channel: ReminderChannel
    send_at: datetime
    status: ReminderStatus
    sent_at: datetime | None

    model_config = {"from_attributes": True}


class ReminderStatusUpdate(BaseModel):
    status: ReminderStatus
