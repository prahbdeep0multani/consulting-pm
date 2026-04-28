import redis.asyncio as aioredis

from .schemas.base import BaseEvent

STREAM_AUTH = "events:auth"
STREAM_PROJECTS = "events:projects"
STREAM_TIMELOG = "events:timelog"
STREAM_BILLING = "events:billing"
STREAM_RESOURCES = "events:resources"


class EventPublisher:
    def __init__(self, redis_client: aioredis.Redis) -> None:
        self._redis = redis_client

    async def publish(self, stream: str, event: BaseEvent) -> str:
        """XADD event to stream. Returns the stream entry ID."""
        msg_id: str = await self._redis.xadd(  # type: ignore[assignment]
            stream, event.to_stream_dict(), maxlen=10_000, approximate=True
        )
        return msg_id

    async def publish_auth(self, event: BaseEvent) -> str:
        return await self.publish(STREAM_AUTH, event)

    async def publish_projects(self, event: BaseEvent) -> str:
        return await self.publish(STREAM_PROJECTS, event)

    async def publish_timelog(self, event: BaseEvent) -> str:
        return await self.publish(STREAM_TIMELOG, event)

    async def publish_billing(self, event: BaseEvent) -> str:
        return await self.publish(STREAM_BILLING, event)

    async def publish_resources(self, event: BaseEvent) -> str:
        return await self.publish(STREAM_RESOURCES, event)
