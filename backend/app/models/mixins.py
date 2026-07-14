import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPKMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class TenantScopedMixin:
    """Mix into any model whose rows belong to a single clinic.

    Every repository/service function that queries a tenant-scoped table
    must take clinic_id as an explicit, mandatory argument and filter on it
    (see app/core/tenancy.py) - never rely on implicit/global scoping.
    """

    clinic_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clinics.id"), nullable=False, index=True)
