"""Realtime Notification service.

Persists notification records to the database and broadcasts live updates
via Redis pub/sub to active client SSE sessions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models.notification import Notification
from app.realtime.pubsub import publish_notification

logger = get_logger()


class NotificationService:
    @staticmethod
    async def create_and_dispatch(
        *,
        db: AsyncSession,
        redis: Redis | None,
        user_id: str,
        org_id: str,
        kind: str,
        title: str,
        body: str,
        analysis_id: str | None = None,
        href: str | None = None,
    ) -> Notification:
        notification = Notification(
            id=f"n_{uuid.uuid4().hex[:10]}",
            user_id=user_id,
            org_id=org_id,
            kind=kind,
            title=title,
            body=body,
            read=False,
            analysis_id=analysis_id,
            href=href or (f"/app/analyses/{analysis_id}" if analysis_id else "/app/analyses"),
        )
        db.add(notification)
        await db.flush()

        logger.info("notification_created", user_id=user_id, kind=kind, title=title)

        if redis:
            payload = {
                "id": notification.id,
                "at": datetime.now(UTC).isoformat(),
                "kind": notification.kind,
                "title": notification.title,
                "body": notification.body,
                "read": False,
                "analysisId": notification.analysis_id,
                "href": notification.href,
            }
            try:
                await publish_notification(redis, user_id, payload)
            except Exception as e:
                logger.warning("notification_dispatch_failed", error=str(e))

        return notification
