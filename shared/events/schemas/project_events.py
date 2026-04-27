import uuid
from datetime import date

from .base import BaseEvent


class ProjectCreatedEvent(BaseEvent):
    event_type: str = "project.created"
    source_service: str = "projects"
    project_id: uuid.UUID
    name: str
    type: str
    client_id: uuid.UUID
    manager_user_id: uuid.UUID
    budget_amount: str | None
    currency: str
    start_date: date
    end_date: date | None


class ProjectStatusChangedEvent(BaseEvent):
    event_type: str = "project.status_changed"
    source_service: str = "projects"
    project_id: uuid.UUID
    old_status: str
    new_status: str
    changed_by: uuid.UUID


class TaskCreatedEvent(BaseEvent):
    event_type: str = "task.created"
    source_service: str = "projects"
    task_id: uuid.UUID
    project_id: uuid.UUID
    title: str
    assignee_user_id: uuid.UUID | None
    reporter_user_id: uuid.UUID
    priority: str
    due_date: date | None


class TaskAssignedEvent(BaseEvent):
    event_type: str = "task.assigned"
    source_service: str = "projects"
    task_id: uuid.UUID
    project_id: uuid.UUID
    old_assignee_user_id: uuid.UUID | None
    new_assignee_user_id: uuid.UUID
    assigned_by: uuid.UUID


class TaskStatusChangedEvent(BaseEvent):
    event_type: str = "task.status_changed"
    source_service: str = "projects"
    task_id: uuid.UUID
    project_id: uuid.UUID
    old_status: str
    new_status: str
    changed_by: uuid.UUID


class MilestoneCompletedEvent(BaseEvent):
    event_type: str = "milestone.completed"
    source_service: str = "projects"
    milestone_id: uuid.UUID
    project_id: uuid.UUID
    name: str
    completed_by: uuid.UUID
