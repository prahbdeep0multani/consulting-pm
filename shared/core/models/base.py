import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import UUID, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_tenant_id_var: ContextVar[uuid.UUID | None] = ContextVar("tenant_id", default=None)


def get_current_tenant_id() -> uuid.UUID:
    tid = _tenant_id_var.get()
    if tid is None:
        raise RuntimeError("No tenant context set — missing TenantMiddleware?")
    return tid


def set_tenant_id(tenant_id: uuid.UUID) -> None:
    _tenant_id_var.set(tenant_id)


def clear_tenant_id() -> None:
    _tenant_id_var.set(None)


class Base(DeclarativeBase):
    type_annotation_map: dict[Any, Any] = {
        uuid.UUID: UUID(as_uuid=True),
    }


class PrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        sort_order=-10,
    )


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        sort_order=100,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        sort_order=101,
    )


class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        sort_order=102,
    )


class TenantMixin:
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        sort_order=-9,
    )
