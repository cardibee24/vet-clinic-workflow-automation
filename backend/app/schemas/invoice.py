import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field, computed_field

from app.models.invoice import InvoiceStatus, PaymentMethod


class LineItemCreate(BaseModel):
    description: str
    quantity: int = Field(default=1, ge=1)
    unit_price_cents: int = Field(ge=0)


class LineItemUpdate(BaseModel):
    description: str | None = None
    quantity: int | None = Field(default=None, ge=1)
    unit_price_cents: int | None = Field(default=None, ge=0)


class LineItemOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    description: str
    quantity: int
    unit_price_cents: int

    model_config = {"from_attributes": True}

    @computed_field
    @property
    def amount_cents(self) -> int:
        return self.quantity * self.unit_price_cents


class InvoiceCreate(BaseModel):
    owner_id: uuid.UUID
    appointment_id: uuid.UUID | None = None
    due_date: date | None = None
    notes: str | None = None


class InvoiceOut(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    appointment_id: uuid.UUID | None
    status: InvoiceStatus
    issued_at: datetime | None
    due_date: date | None
    notes: str | None
    paid_at: datetime | None
    payment_method: PaymentMethod | None

    model_config = {"from_attributes": True}


class InvoiceWithLineItems(InvoiceOut):
    line_items: list[LineItemOut] = []

    @computed_field
    @property
    def total_cents(self) -> int:
        return sum(item.amount_cents for item in self.line_items)


class InvoiceListOut(InvoiceOut):
    total_cents: int


class InvoiceStatusUpdate(BaseModel):
    status: InvoiceStatus
    payment_method: PaymentMethod | None = None


class CommonLineItem(BaseModel):
    description: str
    unit_price_cents: int


class DraftLineItemsRequest(BaseModel):
    notes: str
