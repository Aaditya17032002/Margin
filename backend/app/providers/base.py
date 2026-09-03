"""Provider interfaces — abstract base classes for all external services.

These interfaces allow swapping between Azure (prod) and Mock (dev/CI) providers
via env config. The mock provider runs the full workflow offline.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChunkResult:
    text: str
    page: int
    section_path: str
    bbox: dict | None = None
    chunk_index: int = 0


@dataclass
class LayoutResult:
    pages: list[dict]  # [{page, heading, lines}]
    chunks: list[ChunkResult] = field(default_factory=list)
    page_count: int = 0
    raw_text: str = ""


@dataclass
class EmbeddingResult:
    embedding: list[float]
    text: str
    chunk_id: str = ""


@dataclass
class RetrievalResult:
    text: str
    page: int
    section_path: str
    bbox: dict | None = None
    score: float = 0.0


@dataclass
class AgentResult:
    """Result from a specialist agent run."""
    findings: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class ResearchResult:
    """Result from external research (Deep Research / Bing)."""
    findings: list[dict] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)
    query_used: str = ""


class DocIntelProvider(ABC):
    """Document Intelligence — layout extraction."""

    @abstractmethod
    async def extract_layout(self, content: bytes, filename: str) -> LayoutResult:
        ...


class LLMProvider(ABC):
    """LLM for agent reasoning."""

    @abstractmethod
    async def complete(self, messages: list[dict], *, model: str | None = None, **kwargs: Any) -> str:
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...


class AgentProvider(ABC):
    """Multi-agent orchestration."""

    @abstractmethod
    async def run_specialist(
        self, agent_id: str, schema_slice: dict, chunks: list[ChunkResult], **kwargs: Any
    ) -> AgentResult:
        ...

    @abstractmethod
    async def verify(self, findings: list[dict], chunks: list[ChunkResult]) -> list[dict]:
        ...


class SearchProvider(ABC):
    """Vector search over document chunks."""

    @abstractmethod
    async def search(self, query: str, analysis_id: str, top_k: int = 10) -> list[RetrievalResult]:
        ...


class ResearchProvider(ABC):
    """External research — Deep Research + Grounding with Bing.

    COMPLIANCE: Only generic, derived query strings may be sent.
    Raw document text must NEVER pass through this provider.
    """

    @abstractmethod
    async def research(self, query: str) -> ResearchResult:
        """Execute research on a generic, derived query. The query must NOT
        contain raw solicitation text — only extracted generic concepts."""
        ...
