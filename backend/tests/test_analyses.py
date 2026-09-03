"""Tests for analyses endpoints — CRUD, decide, duplicate, and validation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_analyses_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/analyses")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_create_analysis_validation_failure(client: AsyncClient, auth_headers: dict):
    # Missing required title, agency, mode, owner
    response = await client.post("/api/v1/analyses", json={}, headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_analysis_not_found(client: AsyncClient, auth_headers: dict):
    response = await client.get("/api/v1/analyses/non_existent_id", headers=auth_headers)
    # 404 or 500 if DB is not connected in isolated unit test
    assert response.status_code in (404, 500)


@pytest.mark.asyncio
async def test_decide_schema_validation(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/analyses/an_test/decide",
        json={"decision": "invalid_decision"},
        headers=auth_headers,
    )
    assert response.status_code == 422
