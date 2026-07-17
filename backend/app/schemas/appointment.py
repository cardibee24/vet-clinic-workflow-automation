import uuid
from datetime import datetime

from pydantic import BaseModel, model_validator

from app.models.appointment import AppointmentStatus


class AppointmentCreate(BaseModel):
    pet_id: uuid.UUID
    assigned_user_id: uuid.UUID | None = None
    scheduled_start: datetime
    scheduled_end: datetime
    reason: str | None = None

    @model_validator(mode="after")
    def check_time_range(self) -> "AppointmentCreate":
        if self.scheduled_end <= self.scheduled_start:
            raise ValueError("scheduled_end must be after scheduled_start")
        return self


class AppointmentOut(BaseModel):
    id: uuid.UUID
    clinic_id: uuid.UUID
    pet_id: uuid.UUID
    assigned_user_id: uuid.UUID | None
    scheduled_start: datetime
    scheduled_end: datetime
    status: AppointmentStatus
    reason: str | None

    model_config = {"from_attributes": True}


class AppointmentStatusUpdate(BaseModel):
    status: AppointmentStatus
