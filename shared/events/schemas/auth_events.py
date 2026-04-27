import uuid

from .base import BaseEvent


class TenantCreatedEvent(BaseEvent):
    event_type: str = "tenant.created"
    source_service: str = "auth"
    slug: str
    name: str
    plan: str


class UserRegisteredEvent(BaseEvent):
    event_type: str = "user.registered"
    source_service: str = "auth"
    user_id: uuid.UUID
    email: str
    full_name: str
    roles: list[str]


class UserDeactivatedEvent(BaseEvent):
    event_type: str = "user.deactivated"
    source_service: str = "auth"
    user_id: uuid.UUID
