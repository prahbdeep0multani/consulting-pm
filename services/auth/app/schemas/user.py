import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from shared.core.schemas.base import BaseSchema


class RoleRef(BaseSchema):
    id: uuid.UUID
    name: str


class UserCreate(BaseSchema):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=255)
    role_names: list[str] = ["consultant"]


class UserInvite(BaseSchema):
    email: EmailStr
    full_name: str
    role_names: list[str] = ["consultant"]


class UserUpdate(BaseSchema):
    full_name: str | None = None
    avatar_url: str | None = None


class UserResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    email: str
    full_name: str
    avatar_url: str | None
    is_active: bool
    is_verified: bool
    last_login_at: datetime | None
    roles: list[RoleRef] = []
    created_at: datetime
