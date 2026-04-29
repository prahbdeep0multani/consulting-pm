import json
from typing import Any

import redis.asyncio as aioredis


class RedisCache:
    def __init__(self, url: str) -> None:
        self._client: aioredis.Redis = aioredis.from_url(url, decode_responses=True)

    async def get(self, key: str) -> Any | None:
        value = await self._client.get(key)
        if value is None:
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        serialized = json.dumps(value) if not isinstance(value, str) else value
        if ttl:
            await self._client.setex(key, ttl, serialized)
        else:
            await self._client.set(key, serialized)

    async def delete(self, key: str) -> None:
        await self._client.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._client.exists(key))

    async def incr(self, key: str) -> int:
        return int(await self._client.incr(key))

    async def expire(self, key: str, ttl: int) -> None:
        await self._client.expire(key, ttl)

    async def ping(self) -> bool:
        try:
            await self._client.ping()  # type: ignore[misc]
            return True
        except Exception:
            return False

    async def close(self) -> None:
        await self._client.aclose()  # type: ignore[attr-defined]

    @property
    def client(self) -> aioredis.Redis:
        return self._client


_redis_instance: RedisCache | None = None


def get_redis() -> RedisCache:
    if _redis_instance is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_instance


def init_redis(url: str) -> RedisCache:
    global _redis_instance
    _redis_instance = RedisCache(url)
    return _redis_instance
