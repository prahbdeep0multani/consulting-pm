import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from shared.core.schemas.base import BaseSchema, TimestampSchema


class AllocationCreate(BaseSchema):
    user_id: uuid.UUID
    project_id: uuid.UUID
    role_on_project: str | None = None
    allocation_pct: int = Field(ge=0, le=100)
    start_date: date
    end_date: date | None = None
    notes: str | None = None


class AllocationUpdate(BaseSchema):
    allocation_pct: int | None = Field(default=None, ge=0, le=100)
    end_date: date | None = None
    notes: str | None = None


class AllocationResponse(TimestampSchema):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    role_on_project: str | None
    allocation_pct: int
    start_date: date
    end_date: date | None
    notes: str | None


class LeaveRequestCreate(BaseSchema):
    type: str
    start_date: date
    end_date: date
    total_days: Decimal = Field(gt=0)
    notes: str | None = None


class LeaveRequestUpdate(BaseSchema):
    type: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    total_days: Decimal | None = None
    notes: str | None = None


class RejectLeaveRequest(BaseSchema):
    rejection_reason: str | None = None


class LeaveRequestResponse(TimestampSchema):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    type: str
    start_date: date
    end_date: date
    total_days: Decimal
    status: str
    approver_user_id: uuid.UUID | None
    approved_at: datetime | None
    rejection_reason: str | None
