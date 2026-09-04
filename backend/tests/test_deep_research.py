"""Deep research must survive a rate limit instead of silently producing nothing."""

from __future__ import annotations

import httpx
import pytest

from app.providers.azure import AzureResearchProvider, outcome_retry_delay
from app.providers.base import ResearchResult


def _provider(handler) -> AzureResearchProvider:
    provider = AzureResearchProvider(
        endpoint="https://example.invalid",
        api_key="k",
        poll_seconds=0.0,
        max_wait_seconds=1.0,
        max_attempts=3,
        retry_base_seconds=0.0,
    )
    provider._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return provider


def _job(status: str, error: dict | None = None, text: str = "") -> dict:
    body: dict = {"id": "resp_1", "status": status}
    if error:
        body["error"] = error
    if text:
        body["output"] = [{"type": "message", "content": [{"type": "output_text", "text": text}]}]
    return body


@pytest.mark.asyncio
async def test_a_rate_limited_job_is_retried_and_then_succeeds():
    """The exact failure seen in production: the job is accepted, then comes
    back `failed` with rate_limit_exceeded minutes later."""
    attempts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            attempts["n"] += 1
            return httpx.Response(200, json=_job("queued"))
        if attempts["n"] == 1:
            return httpx.Response(
                200,
                json=_job("failed", {"code": "rate_limit_exceeded", "message": "exceeded rate limit"}),
            )
        return httpx.Response(200, json=_job("completed", text="Procurement rules summary."))

    result = await _provider(handler).research("query")
    assert result.status == "completed"
    assert attempts["n"] == 2
    assert result.findings and "Procurement" in result.findings[0]["summary"]


@pytest.mark.asyncio
async def test_a_persistent_rate_limit_reports_itself_rather_than_looking_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(200, json=_job("queued"))
        return httpx.Response(
            200, json=_job("failed", {"code": "rate_limit_exceeded", "message": "exceeded rate limit"})
        )

    result = await _provider(handler).research("query")
    assert result.status == "rate_limited"
    assert "rate limit" in result.detail
    assert result.findings == []


@pytest.mark.asyncio
async def test_a_429_on_create_is_also_a_rate_limit():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            return httpx.Response(429, headers={"retry-after": "2"}, json={"error": "slow down"})
        return httpx.Response(200, json=_job("completed"))

    result = await _provider(handler).research("query")
    assert result.status == "rate_limited"


@pytest.mark.asyncio
async def test_a_bad_request_is_not_retried():
    """Our mistake will not fix itself, so waiting on it only wastes the run."""
    posts = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            posts["n"] += 1
            return httpx.Response(400, json={"error": "unknown model"})
        return httpx.Response(200, json=_job("completed"))

    result = await _provider(handler).research("query")
    assert result.status == "failed"
    assert posts["n"] == 1


@pytest.mark.asyncio
async def test_missing_configuration_is_skipped_not_failed():
    provider = AzureResearchProvider(endpoint="", api_key="")
    result = await provider.research("query")
    assert result.status == "skipped"


def test_retry_delay_honours_retry_after_and_otherwise_backs_off():
    honoured = outcome_retry_delay(
        ResearchResult(status="rate_limited", detail="retry-after=45"), base=20.0, attempt=1
    )
    assert honoured == 45.0

    first = outcome_retry_delay(ResearchResult(status="rate_limited"), base=20.0, attempt=1)
    third = outcome_retry_delay(ResearchResult(status="rate_limited"), base=20.0, attempt=3)
    assert 16 <= first <= 24
    assert third > first
