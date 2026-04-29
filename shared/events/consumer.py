import asyncio
import json
import logging
from collections.abc import Callable, Coroutine
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

EventHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class EventConsumer:
    """Redis Streams consumer group reader with automatic XAUTOCLAIM for stale messages."""

    def __init__(
        self,
        redis_client: aioredis.Redis,
        service_name: str,
        streams: list[str],
        batch_size: int = 10,
        block_ms: int = 5_000,
        stale_claim_ms: int = 60_000,
    ) -> None:
        self._redis = redis_client
        self._service = service_name
        self._streams = streams
        self._batch_size = batch_size
        self._block_ms = block_ms
        self._stale_claim_ms = stale_claim_ms
        self._handlers: dict[str, EventHandler] = {}
        self._running = False

    def register(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type] = handler

    async def _ensure_groups(self) -> None:
        for stream in self._streams:
            try:
                await self._redis.xgroup_create(stream, self._service, id="0", mkstream=True)
            except Exception as e:
                logger.debug("Stream consumer group already exists for %s: %s", stream, e)

    async def start(self) -> None:
        await self._ensure_groups()
        self._running = True
        stream_ids = dict.fromkeys(self._streams, ">")
        while self._running:
            try:
                results = await self._redis.xreadgroup(
                    self._service,
                    f"{self._service}-consumer-1",
                    stream_ids,  # type: ignore[arg-type]
                    count=self._batch_size,
                    block=self._block_ms,
                )
                if results:
                    for stream, messages in results:
                        for msg_id, fields in messages:
                            await self._handle_message(stream, msg_id, fields)
                await self._reclaim_stale()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Consumer error: %s", e)
                await asyncio.sleep(1)

    async def _handle_message(self, stream: str, msg_id: str, fields: dict[str, str]) -> None:
        try:
            data = json.loads(fields.get("data", "{}"))
            event_type = data.get("event_type", "")
            handler = self._handlers.get(event_type)
            if handler:
                await handler(data)
            await self._redis.xack(stream, self._service, msg_id)
        except Exception as e:
            logger.error("Failed to handle message %s: %s", msg_id, e)

    async def _reclaim_stale(self) -> None:
        for stream in self._streams:
            try:
                await self._redis.xautoclaim(
                    stream,
                    self._service,
                    f"{self._service}-consumer-1",
                    self._stale_claim_ms,
                    "0-0",
                    count=self._batch_size,
                )
            except Exception as e:
                logger.debug("Failed to reclaim stale messages from %s: %s", stream, e)

    def stop(self) -> None:
        self._running = False
