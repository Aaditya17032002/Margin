"""Verifier logic tests — ensures the verifier downgrades unsupported findings."""

from __future__ import annotations

import pytest

from app.providers.mock import MockAgentProvider
from app.providers.base import ChunkResult


SOURCE_TEXT = "Proposals shall be submitted in three separate volumes before the deadline."


def cite(quote: str) -> dict:
    return {
        "id": "c_1",
        "page": 1,
        "section": "Section L",
        "quote": quote,
        "bbox": {"x": 0.1, "y": 0.1, "w": 0.8, "h": 0.05},
    }


@pytest.mark.asyncio
async def test_verifier_marks_high_confidence_as_verified():
    provider = MockAgentProvider()
    findings = [
        {"id": "f_1", "label": "Test", "value": "val", "confidence": 0.95, "stakes": "scored",
         "citation": cite("Proposals shall be submitted in three separate volumes")},
        {"id": "f_2", "label": "Test2", "value": "val2", "confidence": 0.88, "stakes": "informational",
         "citation": cite("submitted in three separate volumes")},
    ]
    chunks = [ChunkResult(text=SOURCE_TEXT, page=1, section_path="A")]

    verified = await provider.verify(findings, chunks)

    assert all(f["verified"] for f in verified)
    assert all(not f.get("flagged") for f in verified)


@pytest.mark.asyncio
async def test_verifier_flags_a_finding_with_no_quote():
    """A claim that cannot point at a line is never merely trusted."""
    provider = MockAgentProvider()
    findings = [{"id": "f_1", "label": "Unsourced", "value": "v", "confidence": 0.99, "stakes": "scored"}]
    chunks = [ChunkResult(text=SOURCE_TEXT, page=1, section_path="A")]

    verified = await provider.verify(findings, chunks)

    assert not verified[0]["verified"]
    assert verified[0]["flagged"]
    assert verified[0]["state"] == "NEEDS_HUMAN"


@pytest.mark.asyncio
async def test_verifier_flags_a_quote_absent_from_the_source():
    provider = MockAgentProvider()
    findings = [
        {"id": "f_1", "label": "Invented", "value": "v", "confidence": 0.97, "stakes": "scored",
         "citation": cite("Offerors receive unlimited government furnished equipment")},
    ]
    chunks = [ChunkResult(text=SOURCE_TEXT, page=1, section_path="A")]

    verified = await provider.verify(findings, chunks)

    assert not verified[0]["verified"]
    assert verified[0]["flagged"]


@pytest.mark.asyncio
async def test_verifier_downgrades_low_confidence():
    provider = MockAgentProvider()
    findings = [
        {"id": "f_1", "label": "Weak", "value": "unsure", "confidence": 0.3, "stakes": "scored",
         "citation": cite("Proposals shall be submitted in three separate volumes")},
    ]
    chunks = [ChunkResult(text=SOURCE_TEXT, page=1, section_path="A")]

    verified = await provider.verify(findings, chunks)

    assert not verified[0]["verified"]
    assert verified[0]["flagged"]


@pytest.mark.asyncio
async def test_verifier_preserves_all_fields():
    provider = MockAgentProvider()
    findings = [
        {"id": "f_1", "label": "Test", "value": "v", "confidence": 0.9,
         "stakes": "disqualifying", "detail": "extra info",
         "citation": cite("Proposals shall be submitted in three separate volumes")},
    ]
    chunks = [ChunkResult(text=SOURCE_TEXT, page=1, section_path="A")]

    verified = await provider.verify(findings, chunks)

    assert verified[0]["detail"] == "extra info"
    assert verified[0]["stakes"] == "disqualifying"
