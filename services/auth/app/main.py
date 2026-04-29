from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from shared.core.exceptions import register_exception_handlers
from shared.core.health import create_health_router
from shared.core.middleware import CorrelationIdMiddleware, TenantMiddleware
from shared.core.security.jwt import JWTHandler

from .config import settings
from .database import check_db, init_db
from .routers import auth_router, roles_router, tenants_router, users_router

jwt_handler: JWTHandler = None  # type: ignore[assignment]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global jwt_handler
    init_db(settings.database_url)
    jwt_handler = JWTHandler(
        private_key=settings.get_private_key(),
        public_key=settings.get_public_key(),
        access_token_expire_minutes=settings.access_token_expire_minutes,
        refresh_token_expire_days=settings.refresh_token_expire_days,
    )
    yield


app = FastAPI(
    title="Auth Service",
    description="Multi-tenant authentication & authorization",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(TenantMiddleware)

register_exception_handlers(app)


async def _check_db() -> bool:
    return bool(await check_db())


app.include_router(create_health_router("auth", [("database", _check_db)]))
app.include_router(tenants_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(roles_router)
