from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from shared.core.exceptions import AuthenticationError
from shared.core.security.jwt import JWTHandler

_PUBLIC_PATHS = {"/health", "/ready", "/docs", "/openapi.json", "/redoc"}

# Auth endpoints that don't require a valid access token
_AUTH_PUBLIC_PREFIXES = (
    "/auth/login",
    "/auth/refresh",
    "/auth/forgot-password",
    "/auth/reset-password",
    "/auth/verify-email",
    "/tenants",
)


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validates RS256 JWT access tokens and injects user context headers."""

    def __init__(
        self, app: object, jwt_handler: JWTHandler, public_prefixes: tuple[str, ...] = ()
    ) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._jwt = jwt_handler
        self._public_prefixes = _AUTH_PUBLIC_PREFIXES + public_prefixes

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        if path in _PUBLIC_PATHS or any(path.startswith(p) for p in self._public_prefixes):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "authentication_error",
                    "message": "Missing or malformed Authorization header",
                },
            )

        token = auth_header.removeprefix("Bearer ")
        try:
            claims = self._jwt.decode_access_token(token)
        except AuthenticationError as e:
            return JSONResponse(
                status_code=401,
                content={"error": "authentication_error", "message": str(e)},
            )

        # Inject headers for downstream use (FastAPI Depends)
        request.state.user_id = claims.sub
        request.state.tenant_id = claims.tenant_id
        request.state.roles = claims.roles
        request.state.permissions = claims.permissions

        return await call_next(request)
