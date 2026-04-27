import uuid
from datetime import date

from .base import BaseEvent


class AllocationCreatedEvent(BaseEvent):
    event_type: str = "allocation.created"
    source_service: str = "resources"
    allocation_id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    allocation_pct: int
    start_date: date
    end_date: date | None


class LeaveRequestApprovedEvent(BaseEvent):
    event_type: str = "leave_request.approved"
    source_service: str = "resources"
    leave_request_id: uuid.UUID
    user_id: uuid.UUID
    start_date: date
    end_date: date
    total_days: float
    type: str
