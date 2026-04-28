import uuid

from fastapi import Request
from shared.core.exceptions import AuthenticationError
from shared.core.models.base import set_tenant_id


def get_current_user_id(request: Request) -> uuid.UUID:
    user_id_str = getattr(request.state, "user_id", None)
    if not user_id_str:
        raise AuthenticationError("Not authenticated")
    return uuid.UUID(user_id_str)


def get_current_tenant_id_dep(request: Request) -> uuid.UUID:
    """Ensures tenant context is set from request state (injected by gateway)."""
    tenant_id_str = getattr(request.state, "tenant_id", None) or request.headers.get("X-Tenant-ID")
    if not tenant_id_str:
        raise AuthenticationError("Tenant context missing")
    tid = uuid.UUID(tenant_id_str)
    set_tenant_id(tid)
    return tid
