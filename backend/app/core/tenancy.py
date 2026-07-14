"""Multi-tenancy convention for this codebase.

Tenant isolation is enforced at the query/service layer, not via Postgres
row-level security. Every model that stores per-clinic data uses
TenantScopedMixin (app/models/mixins.py). Every repository/service function
that reads or writes such a table MUST take clinic_id as an explicit,
mandatory argument and apply it with `scoped()` below - never infer the
current clinic implicitly (e.g. from a global/thread-local), since that is
how cross-tenant data leaks happen.
"""

import uuid

from sqlalchemy import Select


def scoped(stmt: Select, model: type, clinic_id: uuid.UUID) -> Select:
    return stmt.where(model.clinic_id == clinic_id)
