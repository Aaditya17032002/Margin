"""Server-Sent Events (SSE) streaming helpers for agent choreography and notifications."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from redis.asyncio import Redis

from app.core.logging import get_logger

logger = get_logger()


async def stream_redis_channel(
    redis: Redis,
    channel_name: str,
    ping_interval: float = 15.0,
) -> AsyncGenerator[dict[str, Any], None]:
    """Relays messages from a Redis pub/sub channel as SSE frames with periodic keep-alive pings."""
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel_name)
    logger.debug("sse_subscribed", channel=channel_name)

    try:
        while True:
            try:
                # Wait for message with a short timeout to allow pings
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                    timeout=ping_interval,
                )
                if message and message.get("type") == "message":
                    yield {
                        "event": "message",
                        "data": message["data"],
                    }
                else:
                    yield {
                        "event": "ping",
                        "data": "",
                    }
            except TimeoutError:
                yield {
                    "event": "ping",
                    "data": "",
                }
            await asyncio.sleep(0.05)
    finally:
        await pubsub.unsubscribe(channel_name)
        await pubsub.aclose()
        logger.debug("sse_unsubscribed", channel=channel_name)
