"""Notifications router — CRUD + read-all + SSE stream."""

from __future__ import annotations

import asyncio
import uuid
from typing import AsyncGenerator

import orjson
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select, update
from sse_starlette.sse import EventSourceResponse

from app.core.deps import CurrentUser, DbSession, RedisClient
from app.db.models.notification import Notification
from app.schemas.resources import (
    NotificationCreate,
    NotificationResponse,
    NotificationUpdate,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _to_response(n: Notification) -> dict:
    from datetime import datetime
    return {
        "id": n.id,
        "at": n.created_at.isoformat() if isinstance(n.created_at, datetime) else str(n.created_at),
        "kind": n.kind,
        "title": n.title,
        "body": n.body,
        "read": n.read,
        "analysisId": n.analysis_id,
        "href": n.href,
    }


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user.id, Notification.org_id == user.org_id)
        .order_by(Notification.created_at.desc())
        .limit(100)
    )
    return [_to_response(n) for n in result.scalars().all()]


@router.post("", status_code=status.HTTP_201_CREATED, response_model=NotificationResponse)
async def create_notification(body: NotificationCreate, user: CurrentUser, db: DbSession, redis: RedisClient):
    """Raise a notification for the signed-in user."""
    n = Notification(
        id=f"n_{uuid.uuid4().hex[:8]}",
        user_id=user.id,
        org_id=user.org_id,
        kind=body.kind,
        title=body.title,
        body=body.body,
        read=False,
        analysis_id=body.analysis_id,
        href=body.href,
    )
    db.add(n)
    await db.flush()

    payload = _to_response(n)
    await redis.publish(f"notifications:{user.id}", orjson.dumps(payload).decode())
    return payload


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_all(user: CurrentUser, db: DbSession):
    await db.execute(
        delete(Notification).where(
            Notification.user_id == user.id, Notification.org_id == user.org_id
        )
    )
    await db.flush()


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(notification_id: str, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user.id
        )
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    await db.delete(n)


@router.patch("/{notification_id}")
async def update_notification(notification_id: str, body: NotificationUpdate, user: CurrentUser, db: DbSession):
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id, Notification.user_id == user.id
        )
    )
    n = result.scalar_one_or_none()
    if not n:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    if body.read is not None:
        n.read = body.read
    await db.flush()
    return _to_response(n)


@router.post("/read-all")
async def read_all(user: CurrentUser, db: DbSession):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read == False)
        .values(read=True)
    )
    await db.flush()
    return {"status": "ok"}


@router.get("/stream")
async def notification_stream(user: CurrentUser, redis: RedisClient):
    """SSE stream for live notifications."""

    async def event_generator() -> AsyncGenerator[dict, None]:
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"notifications:{user.id}")
        try:
            while True:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    yield {"event": "notification", "data": message["data"]}
                else:
                    yield {"event": "ping", "data": ""}
                await asyncio.sleep(0.5)
        finally:
            await pubsub.unsubscribe(f"notifications:{user.id}")
            await pubsub.aclose()

    return EventSourceResponse(event_generator())
