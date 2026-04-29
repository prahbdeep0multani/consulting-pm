import uuid
from datetime import datetime
from typing import Any

from shared.core.schemas.base import BaseSchema


class NotificationResponse(BaseSchema):
    id: uuid.UUID
    tenant_id: uuid.UUID
    recipient_user_id: uuid.UUID
    type: str
    title: str
    body: str
    payload: dict[str, Any]
    channel: str
    is_read: bool
    read_at: datetime | None
    created_at: datetime


class NotificationPreferenceUpdate(BaseSchema):
    email_enabled: bool | None = None
    in_app_enabled: bool | None = None
    preferences: dict[str, Any][str, Any] | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    timezone: str | None = None


class NotificationPreferenceResponse(BaseSchema):
    id: uuid.UUID
    user_id: uuid.UUID
    email_enabled: bool
    in_app_enabled: bool
    preferences: dict[str, Any]
    timezone: str
