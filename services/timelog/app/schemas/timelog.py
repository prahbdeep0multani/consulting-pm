import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field
from shared.core.schemas.base import BaseSchema, TimestampSchema


class TimeEntryCreate(BaseSchema):
    project_id: uuid.UUID
    task_id: uuid.UUID | None = None
    date: date
    duration_minutes: int = Field(gt=0, le=1440)
    description: str | None = None
    is_billable: bool = True


class TimeEntryUpdate(BaseSchema):
    date: date | None = None
    duration_minutes: int | None = Field(default=None, gt=0, le=1440)
    description: str | None = None
    is_billable: bool | None = None
    task_id: uuid.UUID | None = None


class TimeEntryResponse(TimestampSchema):
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    task_id: uuid.UUID | None
    date: date
    started_at: datetime | None
    ended_at: datetime | None
    duration_minutes: int
    description: str | None
    is_billable: bool
    status: str
    billed_amount: Decimal | None
    invoice_id: uuid.UUID | None


class TimerStopRequest(BaseSchema):
    ended_at: datetime | None = None


class RejectRequest(BaseSchema):
    notes: str | None = None


class ApprovalResponse(BaseSchema):
    id: uuid.UUID
    time_entry_id: uuid.UUID
    approver_user_id: uuid.UUID
    action: str
    notes: str | None
    created_at: datetime
