import uuid
from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from shared.core.models.base import Base
from shared.core.security.jwt import JWTHandler
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

TEST_DB_URL = "postgresql+asyncpg://auth:auth_pass@localhost:5432/auth_test_db"
TEST_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA0Z3VS5JJcds3xHn/ygWep4PAtJZDCCT3BFEF9fVRj5GBMF3i
...test key placeholder - use real key in CI...
-----END RSA PRIVATE KEY-----"""

TEST_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0Z3VS5JJcds3xHn/ygWe
...test key placeholder...
-----END PUBLIC KEY-----"""


@pytest.fixture(scope="session")  # type: ignore[untyped-decorator]
def jwt_handler() -> JWTHandler:
    import os

    private_key = os.environ.get("TEST_JWT_PRIVATE_KEY", TEST_PRIVATE_KEY)
    public_key = os.environ.get("TEST_JWT_PUBLIC_KEY", TEST_PUBLIC_KEY)
    return JWTHandler(private_key=private_key, public_key=public_key)


@pytest_asyncio.fixture(scope="session")  # type: ignore[untyped-decorator]
async def engine() -> AsyncGenerator[AsyncEngine, None]:
    eng = create_async_engine(TEST_DB_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture()  # type: ignore[untyped-decorator]
async def session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as s:
        async with s.begin():
            yield s
            await s.rollback()


@pytest_asyncio.fixture()  # type: ignore[untyped-decorator]
async def client(
    session: AsyncSession, jwt_handler: JWTHandler
) -> AsyncGenerator[AsyncClient, None]:
    import app.main as main_module
    from app.main import app

    main_module.jwt_handler = jwt_handler

    from app.database import get_session

    app.dependency_overrides[get_session] = lambda: session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()  # type: ignore[untyped-decorator]
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()
