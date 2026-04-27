import uuid
from datetime import datetime

from shared.core.schemas.base import BaseSchema


class RoleCreate(BaseSchema):
    name: str
    permissions: list[str] = []


class RoleUpdate(BaseSchema):
    permissions: list[str] | None = None


class RoleResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    is_system: bool
    permissions: list[str]
    created_at: datetime
