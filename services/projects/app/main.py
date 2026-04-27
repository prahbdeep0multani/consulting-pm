from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from shared.core.exceptions import register_exception_handlers
from shared.core.health import create_health_router
from shared.core.middleware import CorrelationIdMiddleware, TenantMiddleware

from .config import settings
from .database import check_db, init_db
from .routers import attachments_router, clients_router, projects_router, tasks_router
from .storage import MinIOStorage

storage: MinIOStorage = None  # type: ignore[assignment]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global storage
    init_db(settings.database_url)
    storage = MinIOStorage(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket=settings.minio_bucket_attachments,
        use_ssl=settings.minio_use_ssl,
    )
    yield


app = FastAPI(title="Projects Service", version="0.1.0", lifespan=lifespan)

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

app.include_router(create_health_router("projects", [("database", check_db)]))
app.include_router(clients_router)
app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(attachments_router)
