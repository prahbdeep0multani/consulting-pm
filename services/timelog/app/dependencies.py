import uuid

from fastapi import Request
from shared.core.exceptions import AuthenticationError
from shared.core.models.base import set_tenant_id


def get_current_user_id(request: Request) -> uuid.UUID:
    uid = getattr(request.state, "user_id", None)
    if not uid:
        raise AuthenticationError("Not authenticated")
    return uuid.UUID(uid)


def get_current_tenant_id_dep(request: Request) -> uuid.UUID:
    tid_str = getattr(request.state, "tenant_id", None) or request.headers.get("X-Tenant-ID")
    if not tid_str:
        raise AuthenticationError("Tenant context missing")
    tid = uuid.UUID(tid_str)
    set_tenant_id(tid)
    return tid


def get_user_roles(request: Request) -> set[str]:
    roles_str = getattr(request.state, "roles", [])
    if isinstance(roles_str, str):
        return set(roles_str.split(","))
    return set(roles_str)
