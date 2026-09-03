"""FastAPI dependency injection — DB session, Redis, current user."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthUser, get_current_user
from app.db.base import async_session_factory

# ── Database session ─────────────────────────────────────────────────────


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ── Redis ────────────────────────────────────────────────────────────────

_redis: Redis | None = None


async def init_redis(url: str) -> Redis:
    global _redis
    _redis = Redis.from_url(url, decode_responses=True)
    await _redis.ping()
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


async def get_redis() -> Redis:
    if _redis is None:
        raise RuntimeError("Redis not initialised — call init_redis() during startup")
    return _redis


# ── Type aliases for Depends ─────────────────────────────────────────────

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
RedisClient = Annotated[Redis, Depends(get_redis)]
