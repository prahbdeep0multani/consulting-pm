import uuid
from datetime import date, datetime
from decimal import Decimal

from shared.core.models.base import (
    Base,
    PrimaryKeyMixin,
    SoftDeleteMixin,
    TenantMixin,
    TimestampMixin,
)
from sqlalchemy import NUMERIC, Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship


class TimeEntry(Base, PrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "time_entries"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    task_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    date: Mapped[date] = mapped_column(Date, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_billable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    billing_rate_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    billed_amount: Mapped[Decimal | None] = mapped_column(NUMERIC(10, 2))
    invoice_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    approvals: Mapped[list["TimeEntryApproval"]] = relationship("TimeEntryApproval", lazy="noload")


class TimeEntryApproval(Base, PrimaryKeyMixin, TenantMixin):
    __tablename__ = "time_entry_approvals"

    time_entry_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("time_entries.id"), nullable=False, index=True
    )
    approver_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # submitted|approved|rejected
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default="now()"
    )
