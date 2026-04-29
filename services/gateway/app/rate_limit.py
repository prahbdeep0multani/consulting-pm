import time

import redis.asyncio as aioredis
from fastapi import Request
from shared.core.exceptions import RateLimitError


class SlidingWindowRateLimiter:
    def __init__(self, redis_client: aioredis.Redis[str], window_seconds: int = 1) -> None:
        self._redis = redis_client
        self._window = window_seconds

    async def check(self, key: str, limit: int) -> None:
        now = int(time.time() * 1000)
        window_start = now - (self._window * 1000)

        pipe = self._redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, self._window + 1)
        results = await pipe.execute()

        count = results[2]
        if count > limit:
            raise RateLimitError(
                f"Rate limit exceeded: {count}/{limit} requests in {self._window}s window"
            )


async def apply_rate_limits(
    request: Request, limiter: SlidingWindowRateLimiter, per_ip: int, per_tenant: int
) -> None:
    client_ip = request.client.host if request.client else "unknown"
    await limiter.check(f"rl:ip:{client_ip}", per_ip)

    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id:
        await limiter.check(f"rl:tenant:{tenant_id}", per_tenant)
