import uuid
from datetime import date

from .base import BaseEvent


class TimeEntrySubmittedEvent(BaseEvent):
    event_type: str = "time_entry.submitted"
    source_service: str = "timelog"
    time_entry_id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    task_id: uuid.UUID | None
    date: date
    duration_minutes: int
    is_billable: bool


class TimeEntryApprovedEvent(BaseEvent):
    event_type: str = "time_entry.approved"
    source_service: str = "timelog"
    time_entry_id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    approver_user_id: uuid.UUID
    duration_minutes: int
    billed_amount: str | None
    billing_rate_id: uuid.UUID | None


class TimeEntryRejectedEvent(BaseEvent):
    event_type: str = "time_entry.rejected"
    source_service: str = "timelog"
    time_entry_id: uuid.UUID
    user_id: uuid.UUID
    approver_user_id: uuid.UUID
    rejection_notes: str | None
