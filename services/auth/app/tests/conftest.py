import uuid
from collections.abc import AsyncGenerator

import app.models  # noqa: F401 - registers models with Base.metadata
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from shared.core.models.base import Base
from shared.core.security.jwt import JWTHandler
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)

TEST_DB_URL = "postgresql+asyncpg://auth:auth_pass@localhost:5432/auth_test_db"
TEST_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEogIBAAKCAQEAr8hWNUgF+7WOI6bB2AI1+suJGF+4XYEgAXLtdlheiv98L8LI
2KRQi/betbAYUTH8sJxwRgVRvOdUk7jXYUt38A4VGiuE/grf0rtNCZiErFLmU3IL
SXEy+9GegOkaYJlSjERIiSG9eNq8U49YWUjBn8peKUu9sZmQLlmghKPrjeosW8Sa
Mu76P6ZxO0MM6Svf5e4XTK6oVz/E7u0pfO7nojdQpUHbd7WONzTdKSD0qsFZXxx9
e0rrY7PdYZBK3fqF1dDw/wDJ21BBEkf6LdMj5cmPRHYGY+Zit8gfT5N5SKTPYnNd
DOvfCM7uB2PM4aZB8SuAZx+9uKTaoOAKWzZOpwIDAQABAoIBAAYW5u2iQ3Ah16e3
2iqVK7Dhe4FYUjcNscHQbRYsH4ep1sUsy++9WXulH2KklA2+sTtJCsFSOS+rGoyi
MEvoOmJwNR5FTa54n/eukg+itKM88p+yFAlaSOLdCHmnbvN+ZulXCuWSlqa+JRyx
RY/qQP2RHCFKxL/coFhgCyXX1owsTDPwdAAtPkeaRxBggYHSQCGAooIyKYhrgPwY
nyRt533NAn+bridB/TzOYThnn+oN39T7KQPMP0ddCKAgPb6701O/oKoNTIUnYKIr
GQ3BbmAfl6L5YmmbKVRqm5lO+BZG1GWdi6cIEDygQ40b1ITcNTKuj6akuk7BaUwE
jpXIn9ECgYEA4FfFGJJblxuQkqmzxkfDTHRRJgfyaQCazEpYDS4N3byBBkZX3qCq
gmQ6b1/p96R2tPTPvlUgCyNbAQqPiYwIOc+HRuGbLaYqxb/Ry6x7ByXWc0mxeD8r
u5yLHifc1G9W4GgNiFhDcdDyEOA16cAi8Ok7xgSMTKYUgC4l7YvXv/8CgYEAyJZc
M2oV8rNDiWZFbpXb+J3EB+odScJma3BYKAd/XGUSrm5N4ZjSYqvk45Fqq8ye2SpA
8e7Pm6ALSK7baLHNYWJN098ogW7HFsrhdyNvxuC6fm3kYoHD+zwFQyqBhw2FaPhz
JM/nA9yCX6+JagZ7Tdk+bwoEgbTRXyK46r6LcVkCgYAKftCvt5klVprK4bmRWyYd
24s4VkLW+rpDOG8qHq9zYjA/FOdjeOzBMOMy9q/BcCZFjPZzFxRqsPq+77mLW8u+
uKDBhih2WEHEApdUCfuvd+uydQ4ibAIlwssXXBIOti7ATN3lNQvitT294F9lUiHQ
V3j+aJQPue1XmdEYbeRoDQKBgGLDzkAukwH+jFmB9tv9g+MFY3l2J9eilaV/GpkT
H/3RcoJao5RaF/UnqDr45eoThX9uU64MJUL+aa/vEO+a5IJ30dRpw9r/PZ4WZS+x
Th9BlfIcj+CE/oecxQaOTlq+KJtIAgH1ME1xbOxKVUHUUTBCsIAiEZf//Tt3sE89
ZRF5AoGAOidPQn5RM4Rsd8m2iK+nB7fVzgjINrJ/ND9eepBEqHBtGWhyNQrXI00i
OW/gPC7738Ht2foucWiwPpdrHXUqwuQvkcS4Je2ikmDgQLyKvqP0DH01Y/EWY1bw
IFImhew9nEXe5A/Vo4Jhwh8va250pYLRNEEGFUDCkPhpoFWpPqo=
-----END RSA PRIVATE KEY-----"""

TEST_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAr8hWNUgF+7WOI6bB2AI1
+suJGF+4XYEgAXLtdlheiv98L8LI2KRQi/betbAYUTH8sJxwRgVRvOdUk7jXYUt3
8A4VGiuE/grf0rtNCZiErFLmU3ILSXEy+9GegOkaYJlSjERIiSG9eNq8U49YWUjB
n8peKUu9sZmQLlmghKPrjeosW8SaMu76P6ZxO0MM6Svf5e4XTK6oVz/E7u0pfO7n
ojdQpUHbd7WONzTdKSD0qsFZXxx9e0rrY7PdYZBK3fqF1dDw/wDJ21BBEkf6LdMj
5cmPRHYGY+Zit8gfT5N5SKTPYnNdDOvfCM7uB2PM4aZB8SuAZx+9uKTaoOAKWzZO
pwIDAQAB
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
    async with engine.connect() as conn:
        await conn.begin()
        s = AsyncSession(
            bind=conn,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield s
        finally:
            await s.close()
            await conn.rollback()


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
