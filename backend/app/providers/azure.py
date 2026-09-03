"""Azure provider stubs — correct interfaces, requires real credentials."""

from __future__ import annotations

from typing import Any

from app.providers.base import (
    AgentProvider,
    AgentResult,
    ChunkResult,
    DocIntelProvider,
    LLMProvider,
    LayoutResult,
    ResearchProvider,
    ResearchResult,
    RetrievalResult,
    SearchProvider,
)


class AzureDocIntelProvider(DocIntelProvider):
    """Azure AI Document Intelligence (Layout) provider."""

    def __init__(self, endpoint: str, key: str):
        self.endpoint = endpoint
        self.key = key

    async def extract_layout(self, content: bytes, filename: str) -> LayoutResult:
        # In production: use azure-ai-documentintelligence SDK
        # client = DocumentIntelligenceClient(endpoint=self.endpoint, credential=AzureKeyCredential(self.key))
        # poller = await client.begin_analyze_document("prebuilt-layout", content)
        # result = await poller.result()
        raise NotImplementedError("Configure AZURE_DOCINTEL_ENDPOINT and AZURE_DOCINTEL_KEY")


class AzureLLMProvider(LLMProvider):
    """Azure OpenAI provider with role-specific deployments."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment: str,
        embedding_deployment: str,
        *,
        api_version: str = "2025-01-01-preview",
        extract_deployment: str | None = None,
        verifier_deployment: str | None = None,
        embedding_api_key: str | None = None,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.api_version = api_version
        self.deployment = deployment
        self.extract_deployment = extract_deployment or deployment
        self.verifier_deployment = verifier_deployment or deployment
        self.embedding_deployment = embedding_deployment
        self.embedding_api_key = embedding_api_key or api_key

    def resolve_deployment(self, model: str | None = None) -> str:
        """Map logical roles → Foundry deployment names."""
        if not model:
            return self.deployment
        key = model.lower().strip()
        if key in {"verifier", "critic", "gpt-5.2-verifier"}:
            return self.verifier_deployment
        if key in {"extract", "specialist", "gpt-5.2"}:
            return self.extract_deployment
        if key in {"router", "cheap", "gpt-4o", "orchestration"}:
            return self.deployment
        return model

    async def complete(self, messages: list[dict], *, model: str | None = None, **kwargs: Any) -> str:
        # In production: use openai.AsyncAzureOpenAI against resolve_deployment(model)
        raise NotImplementedError("Configure AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # In production: use openai.AsyncAzureOpenAI embeddings with embedding_api_key
        raise NotImplementedError("Configure AZURE_OPENAI_ENDPOINT and AZURE_EMBEDDING_API_KEY")


class AzureAgentProvider(AgentProvider):
    """Azure AI Foundry Agent Service for multi-agent orchestration."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        *,
        extract_deployment: str = "gpt-5.2",
        verifier_deployment: str = "gpt-5.2",
        router_deployment: str = "gpt-4o",
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.extract_deployment = extract_deployment
        self.verifier_deployment = verifier_deployment
        self.router_deployment = router_deployment

    async def run_specialist(
        self, agent_id: str, schema_slice: dict, chunks: list[ChunkResult], **kwargs: Any
    ) -> AgentResult:
        # Specialists use extract_deployment (GPT-5.2); routing uses router_deployment
        raise NotImplementedError("Configure Azure AI Foundry credentials")

    async def verify(self, findings: list[dict], chunks: list[ChunkResult]) -> list[dict]:
        # Verifier always uses verifier_deployment (GPT-5.2)
        raise NotImplementedError("Configure Azure AI Foundry credentials")


class AzureSearchProvider(SearchProvider):
    """Azure AI Search for vector similarity."""

    def __init__(self, endpoint: str, key: str):
        self.endpoint = endpoint
        self.key = key

    async def search(self, query: str, analysis_id: str, top_k: int = 10) -> list[RetrievalResult]:
        # In production: use azure-search-documents SDK
        raise NotImplementedError("Configure AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY")


class AzureResearchProvider(ResearchProvider):
    """Azure Deep Research (o3-deep-research) + Grounding with Bing — Norway East."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        *,
        deployment: str = "o3-deep-research",
        region: str = "norwayeast",
        api_version: str = "2025-01-01-preview",
    ):
        self.endpoint = endpoint.rstrip("/") if endpoint else ""
        self.api_key = api_key
        self.deployment = deployment
        self.region = region
        self.api_version = api_version

    async def research(self, query: str) -> ResearchResult:
        # COMPLIANCE: Only generic, derived query strings pass through.
        # Raw document text must NEVER be sent to this provider.
        if not self.endpoint or not self.api_key:
            raise NotImplementedError(
                "Set AZURE_DEEP_RESEARCH_ENDPOINT (norwayeast) and AZURE_DEEP_RESEARCH_API_KEY"
            )
        raise NotImplementedError("Wire Azure Deep Research SDK against o3-deep-research")
