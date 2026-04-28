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
from sqlalchemy import NUMERIC, CheckConstraint, Date, DateTime, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class Allocation(Base, PrimaryKeyMixin, TenantMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "allocations"
    __table_args__ = (
        CheckConstraint("allocation_pct >= 0 AND allocation_pct <= 100", name="chk_allocation_pct"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    role_on_project: Mapped[str | None] = mapped_column(String(100))
    allocation_pct: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)


class LeaveRequest(Base, PrimaryKeyMixin, TenantMixin, TimestampMixin):
    __tablename__ = "leave_requests"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # annual|sick|unpaid|public_holiday|other
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_days: Mapped[Decimal] = mapped_column(NUMERIC(4, 1), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    approver_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
