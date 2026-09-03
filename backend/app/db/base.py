"""SQLAlchemy 2.0 async engine, session factory, and declarative base with UUID PK mixin."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum, MetaData, String, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.config import get_settings

# Naming convention for constraints (Alembic autogenerate friendly)
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def value_enum(*values: str, name: str) -> Enum:
    """A closed set of allowed values, stored as text.

    The schema keeps these columns as VARCHAR rather than native PostgreSQL
    enum types: adding a value to a native enum is a migration and a lock,
    while the set here is product vocabulary that moves with the product.
    Validation still happens — in the API schemas, and on write.
    """
    return Enum(
        *values,
        name=name,
        native_enum=False,
        create_constraint=False,
        validate_strings=True,
    )


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UUIDMixin:
    """Adds a string primary key (UUID-shaped or stable seed ids) and timestamps."""

    id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    # Python-side defaults as well as server ones: a server default is only
    # readable after a round trip, and reading it lazily inside async flush
    # raises. Routers echo the row they just inserted, so the value has to be
    # populated in the identity map already.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class SoftDeleteMixin:
    """Adds a deleted_at column for soft deletes."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )


# ── Engine & session ─────────────────────────────────────────────────────

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine():
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args: dict = {}
        # Neon pooler (PgBouncer) + asyncpg: TLS + disable prepared-statement cache.
        if settings.database_ssl:
            connect_args["ssl"] = True
            connect_args["statement_cache_size"] = 0
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=10,
            max_overflow=5,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
    return _engine


def async_session_factory() -> AsyncSession:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory()


async def init_db() -> None:
    """Create engine and verify connectivity."""
    engine = get_engine()
    async with engine.begin() as conn:
        # Just verify we can connect; migrations handle schema creation
        await conn.execute(func.now())


async def dispose_db() -> None:
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
