import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from shared.core.models.base import clear_tenant_id, set_tenant_id

_PUBLIC_PATHS = {"/health", "/ready", "/docs", "/openapi.json", "/redoc"}


class TenantMiddleware(BaseHTTPMiddleware):
    """Reads X-Tenant-ID header (set by gateway after JWT validation) and
    stores it in a ContextVar so repositories can enforce row-level isolation."""

    async def dispatch(self, request: Request, call_next: object) -> Response:
        if request.url.path in _PUBLIC_PATHS:
            return await call_next(request)  # type: ignore[operator]

        tenant_id_str = request.headers.get("X-Tenant-ID")
        if tenant_id_str:
            try:
                set_tenant_id(uuid.UUID(tenant_id_str))
            except ValueError:
                pass

        try:
            response: Response = await call_next(request)  # type: ignore[operator]
        finally:
            clear_tenant_id()

        return response
