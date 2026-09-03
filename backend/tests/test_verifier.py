"""Verifier logic tests — ensures the verifier downgrades unsupported findings."""

from __future__ import annotations

import pytest

from app.providers.mock import MockAgentProvider
from app.providers.base import ChunkResult


@pytest.mark.asyncio
async def test_verifier_marks_high_confidence_as_verified():
    provider = MockAgentProvider()
    findings = [
        {"id": "f_1", "label": "Test", "value": "val", "confidence": 0.95, "stakes": "scored"},
        {"id": "f_2", "label": "Test2", "value": "val2", "confidence": 0.88, "stakes": "informational"},
    ]
    chunks = [ChunkResult(text="test", page=1, section_path="A")]

    verified = await provider.verify(findings, chunks)

    assert all(f["verified"] for f in verified)
    assert all(not f.get("flagged") for f in verified)


@pytest.mark.asyncio
async def test_verifier_downgrades_low_confidence():
    provider = MockAgentProvider()
    findings = [
        {"id": "f_1", "label": "Weak", "value": "unsure", "confidence": 0.3, "stakes": "scored"},
    ]
    chunks = [ChunkResult(text="test", page=1, section_path="A")]

    verified = await provider.verify(findings, chunks)

    assert not verified[0]["verified"]
    assert verified[0]["flagged"]


@pytest.mark.asyncio
async def test_verifier_preserves_all_fields():
    provider = MockAgentProvider()
    findings = [
        {"id": "f_1", "label": "Test", "value": "v", "confidence": 0.9,
         "stakes": "disqualifying", "detail": "extra info"},
    ]
    chunks = [ChunkResult(text="test", page=1, section_path="A")]

    verified = await provider.verify(findings, chunks)

    assert verified[0]["detail"] == "extra info"
    assert verified[0]["stakes"] == "disqualifying"
