import uuid
from datetime import datetime

from pydantic import Field, field_validator

from shared.core.schemas.base import BaseSchema


class TenantCreate(BaseSchema):
    slug: str = Field(min_length=3, max_length=63, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=2, max_length=255)
    plan: str = "starter"
    admin_email: str
    admin_password: str = Field(min_length=8)
    admin_full_name: str


class TenantUpdate(BaseSchema):
    name: str | None = None
    settings: dict | None = None


class TenantResponse(BaseSchema):
    id: uuid.UUID
    slug: str
    name: str
    plan: str
    is_active: bool
    max_users: int
    created_at: datetime


class TenantStats(BaseSchema):
    user_count: int
    active_user_count: int
    max_users: int
