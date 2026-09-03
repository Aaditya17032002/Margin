"""Test fixtures — async DB session, test client, mock providers."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.core.security import create_token, TokenType


# Override settings for tests
def get_test_settings() -> Settings:
    return Settings(
        APP_ENV="dev",
        DEBUG=True,
        SECRET_KEY="test-secret-key-for-testing-only",
        DB_HOST="localhost",
        DB_PORT=5432,
        DB_USER="margin",
        DB_PASSWORD="margin",
        DB_NAME="margin_test",
        REDIS_HOST="localhost",
        REDIS_PORT=6379,
        PROVIDER_MODE="mock",
    )


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Async test client using ASGI transport."""
    from app.main import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Generate auth headers with a valid access token."""
    token = create_token(
        user_id="u_test",
        org_id="org_test",
        role="admin",
        token_type=TokenType.ACCESS,
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers() -> dict[str, str]:
    """Auth headers for a viewer-role user."""
    token = create_token(
        user_id="u_viewer",
        org_id="org_test",
        role="viewer",
        token_type=TokenType.ACCESS,
    )
    return {"Authorization": f"Bearer {token}"}
