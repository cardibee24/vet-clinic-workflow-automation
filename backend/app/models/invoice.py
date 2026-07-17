import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Enum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base
from app.models.mixins import TenantScopedMixin, TimestampMixin, UUIDPKMixin


class InvoiceStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    PAID = "paid"
    VOID = "void"


class Invoice(Base, UUIDPKMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "invoices"

    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("owners.id"), nullable=False, index=True)
    appointment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("appointments.id"), nullable=True)
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(
            InvoiceStatus,
            name="invoice_status",
            values_callable=lambda enum_cls: [e.value for e in enum_cls],
        ),
        nullable=False,
        default=InvoiceStatus.DRAFT,
        server_default=InvoiceStatus.DRAFT.value,
    )
    issued_at: Mapped[datetime | None] = mapped_column(nullable=True)
    due_date: Mapped[date | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(nullable=True)


class InvoiceLineItem(Base, UUIDPKMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "invoice_line_items"

    invoice_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1, server_default="1")
    unit_price_cents: Mapped[int] = mapped_column(nullable=False)
