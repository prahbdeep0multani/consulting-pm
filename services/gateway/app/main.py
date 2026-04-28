from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from shared.core.exceptions import AuthenticationError, RateLimitError, register_exception_handlers
from shared.core.health import create_health_router
from shared.core.middleware import CorrelationIdMiddleware
from shared.core.security.jwt import JWTHandler

from .config import settings
from .proxy import proxy_request
from .rate_limit import SlidingWindowRateLimiter, apply_rate_limits

_ROUTES: dict[str, str] = {}
_http_client: httpx.AsyncClient | None = None
_redis: aioredis.Redis | None = None
_jwt_handler: JWTHandler | None = None
_rate_limiter: SlidingWindowRateLimiter | None = None

_PUBLIC_AUTH_PREFIXES = (
    "/api/auth/auth/login",
    "/api/auth/auth/refresh",
    "/api/auth/auth/forgot-password",
    "/api/auth/auth/reset-password",
    "/api/auth/tenants",
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _http_client, _redis, _jwt_handler, _rate_limiter, _ROUTES

    _ROUTES = {
        "/api/auth": settings.upstream_auth,
        "/api/projects": settings.upstream_projects,
        "/api/timelog": settings.upstream_timelog,
        "/api/billing": settings.upstream_billing,
        "/api/resources": settings.upstream_resources,
        "/api/notifications": settings.upstream_notifications,
    }

    _http_client = httpx.AsyncClient(timeout=30.0)
    _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    _jwt_handler = JWTHandler(
        private_key="",
        public_key=settings.get_public_key(),
    )
    _rate_limiter = SlidingWindowRateLimiter(_redis)

    yield

    if _http_client:
        await _http_client.aclose()
    if _redis:
        await _redis.aclose()


app = FastAPI(title="API Gateway", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIdMiddleware)

register_exception_handlers(app)


async def _check_redis() -> bool:
    try:
        await _redis.ping()  # type: ignore[union-attr]
        return True
    except Exception:
        return False


app.include_router(create_health_router("gateway", [("redis", _check_redis)]))


@app.api_route(
    "/api/{service}/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
)
async def route(service: str, path: str, request: Request) -> Response:
    prefix = f"/api/{service}"
    upstream = _ROUTES.get(prefix)
    if not upstream:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "message": f"No route for /{service}"},
        )

    # Auth validation (skip for public paths)
    if not any(request.url.path.startswith(p) for p in _PUBLIC_AUTH_PREFIXES):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "authentication_error",
                    "message": "Missing Authorization header",
                },
            )
        try:
            claims = _jwt_handler.decode_access_token(auth_header.removeprefix("Bearer "))  # type: ignore[union-attr]
            request.state.user_id = claims.sub
            request.state.tenant_id = claims.tenant_id
            request.state.roles = claims.roles
        except AuthenticationError as e:
            return JSONResponse(
                status_code=401,
                content={"error": "authentication_error", "message": str(e)},
            )

    # Rate limiting
    try:
        await apply_rate_limits(
            request,
            _rate_limiter,  # type: ignore[arg-type]
            settings.rate_limit_per_ip_rps,
            settings.rate_limit_per_tenant_rps,
        )
    except RateLimitError as e:
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limit_exceeded", "message": str(e)},
        )

    return await proxy_request(request, upstream, _http_client)  # type: ignore[arg-type]
