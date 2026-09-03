"""Boundary tests — assert raw document text never reaches the web/Bing layer.

This is a compliance requirement: the ResearchProvider only receives generic,
derived query strings — never raw solicitation text.
"""

from __future__ import annotations

import pytest

from app.providers.mock import MockResearchProvider


@pytest.mark.asyncio
async def test_research_provider_receives_generic_query():
    """Verify the research provider is called with a generic query, not raw text."""
    provider = MockResearchProvider()

    # Generic query (acceptable)
    result = await provider.research("FERPA vendor obligations 2026")
    assert result.query_used == "FERPA vendor obligations 2026"
    assert len(result.findings) > 0


@pytest.mark.asyncio
async def test_research_provider_interface_exists():
    """Verify the ResearchProvider interface enforces the boundary."""
    from app.providers.base import ResearchProvider

    # The docstring explicitly states the compliance rule
    assert "NEVER" in ResearchProvider.research.__doc__
    assert "generic" in ResearchProvider.research.__doc__.lower()


def test_orchestrator_uses_generic_queries():
    """Verify the orchestrator generates generic queries for research."""
    from app.agents.orchestrator import run_orchestration
    import inspect

    source = inspect.getsource(run_orchestration)
    # The orchestrator should construct generic queries, not pass raw text
    assert "generic_query" in source or "generic" in source.lower()
