from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.core.exceptions import register_exception_handlers
from shared.core.health import create_health_router
from shared.core.middleware import CorrelationIdMiddleware, TenantMiddleware

from .config import settings
from .database import check_db, init_db
from .routers import notifications_router, preferences_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    init_db(settings.database_url)
    yield


app = FastAPI(title="Notifications Service", version="0.1.0", lifespan=lifespan)

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

app.include_router(create_health_router("notifications", [("database", check_db)]))
app.include_router(notifications_router)
app.include_router(preferences_router)
