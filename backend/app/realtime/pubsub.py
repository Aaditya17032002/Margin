"""Redis pub/sub wrapper for streaming events."""

from __future__ import annotations

import orjson
from redis.asyncio import Redis

from app.core.logging import get_logger

logger = get_logger()


async def publish_event(redis: Redis, channel: str, event: dict) -> None:
    """Publish an event to a Redis pub/sub channel."""
    payload = orjson.dumps(event).decode()
    await redis.publish(channel, payload)
    logger.debug("event_published", channel=channel, event=event.get("event"))


async def publish_notification(redis: Redis, user_id: str, notification: dict) -> None:
    """Publish a notification to a user's channel."""
    channel = f"notifications:{user_id}"
    await publish_event(redis, channel, notification)
