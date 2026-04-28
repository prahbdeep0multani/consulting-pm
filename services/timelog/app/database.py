from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

_engine = None
_session_factory = None


def init_db(url: str) -> None:
    global _engine, _session_factory
    _engine = create_async_engine(url, echo=False, pool_pre_ping=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    if _session_factory is None:
        raise RuntimeError("Database not initialized")
    async with _session_factory() as s:
        yield s


async def check_db() -> bool:
    if not _engine:
        return False
    try:
        import sqlalchemy

        async with _engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        return True
    except Exception:
        return False
