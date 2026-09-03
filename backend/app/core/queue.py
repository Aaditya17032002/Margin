"""Arq queue access for the API process.

The API only ever enqueues; the worker container consumes. Keeping the pool
here means a router does not have to know which Redis connection is which.
"""

from __future__ import annotations

from typing import Any

from arq import create_pool
from arq.connections import ArqRedis

from app.core.logging import get_logger
from app.workers.settings import get_redis_settings

logger = get_logger()

_pool: ArqRedis | None = None


async def init_queue() -> ArqRedis:
    global _pool
    _pool = await create_pool(get_redis_settings())
    return _pool


async def close_queue() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


def get_queue() -> ArqRedis | None:
    return _pool


async def enqueue(task: str, *args: Any, **kwargs: Any) -> str | None:
    """Enqueue a worker task. Returns the arq job id, or None when the queue is
    unreachable — callers fall back to reporting the failure rather than
    pretending the work was accepted."""
    pool = get_queue()
    if pool is None:
        logger.error("queue_unavailable", task=task)
        return None
    try:
        job = await pool.enqueue_job(task, *args, **kwargs)
    except Exception as exc:  # noqa: BLE001 — enqueue failure is a caller concern
        logger.error("queue_enqueue_failed", task=task, error=str(exc))
        return None
    return job.job_id if job else None
