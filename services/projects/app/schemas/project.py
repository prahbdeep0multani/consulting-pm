import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from shared.core.schemas.base import BaseSchema, TimestampSchema


class ClientCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    industry: str | None = None
    website: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    billing_address: str | None = None
    currency: str = "USD"
    notes: str | None = None


class ClientUpdate(BaseSchema):
    name: str | None = None
    industry: str | None = None
    contact_email: str | None = None
    notes: str | None = None
    is_active: bool | None = None


class ClientResponse(TimestampSchema):
    tenant_id: uuid.UUID
    name: str
    industry: str | None
    contact_name: str | None
    contact_email: str | None
    currency: str
    is_active: bool


class ProjectCreate(BaseSchema):
    client_id: uuid.UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    type: str  # fixed_price | time_and_materials
    status: str = "planning"
    start_date: date
    end_date: date | None = None
    budget_amount: Decimal | None = None
    currency: str = "USD"
    is_billable: bool = True


class ProjectUpdate(BaseSchema):
    name: str | None = None
    description: str | None = None
    status: str | None = None
    end_date: date | None = None
    budget_amount: Decimal | None = None
    manager_user_id: uuid.UUID | None = None


class ProjectResponse(TimestampSchema):
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    name: str
    description: str | None
    type: str
    status: str
    start_date: date
    end_date: date | None
    budget_amount: Decimal | None
    currency: str
    manager_user_id: uuid.UUID
    is_billable: bool


class MilestoneCreate(BaseSchema):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    due_date: date


class MilestoneUpdate(BaseSchema):
    name: str | None = None
    due_date: date | None = None
    status: str | None = None
    completion_pct: int | None = Field(default=None, ge=0, le=100)


class MilestoneResponse(TimestampSchema):
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    name: str
    due_date: date
    status: str
    completion_pct: int


class TaskCreate(BaseSchema):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    milestone_id: uuid.UUID | None = None
    parent_task_id: uuid.UUID | None = None
    status: str = "todo"
    priority: str = "medium"
    assignee_user_id: uuid.UUID | None = None
    estimated_hours: Decimal | None = None
    due_date: date | None = None
    labels: list[str] = []


class TaskUpdate(BaseSchema):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee_user_id: uuid.UUID | None = None
    milestone_id: uuid.UUID | None = None
    estimated_hours: Decimal | None = None
    due_date: date | None = None
    labels: list[str] | None = None


class TaskResponse(TimestampSchema):
    tenant_id: uuid.UUID
    project_id: uuid.UUID
    milestone_id: uuid.UUID | None
    parent_task_id: uuid.UUID | None
    title: str
    description: str | None
    status: str
    priority: str
    assignee_user_id: uuid.UUID | None
    reporter_user_id: uuid.UUID
    estimated_hours: Decimal | None
    actual_hours: Decimal
    due_date: date | None
    completed_at: datetime | None
    labels: list[str]
    position: int


class CommentCreate(BaseSchema):
    body: str = Field(min_length=1)


class CommentResponse(TimestampSchema):
    tenant_id: uuid.UUID
    task_id: uuid.UUID
    author_user_id: uuid.UUID
    body: str
    edited_at: datetime | None


class AttachmentUploadRequest(BaseSchema):
    filename: str
    content_type: str
    size_bytes: int
    task_id: uuid.UUID | None = None
    project_id: uuid.UUID | None = None


class PresignedUploadResponse(BaseSchema):
    upload_url: str
    attachment_id: uuid.UUID
    expires_in: int = 300


class AttachmentConfirm(BaseSchema):
    attachment_id: uuid.UUID
    checksum_sha256: str | None = None


class AttachmentResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    task_id: uuid.UUID | None
    project_id: uuid.UUID | None
    uploaded_by: uuid.UUID
    created_at: datetime
    download_url: str | None = None
