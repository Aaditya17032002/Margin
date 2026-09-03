"""Provider factory — reads env to select Azure vs mock implementations."""

from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.providers.base import (
    AgentProvider,
    DocIntelProvider,
    LLMProvider,
    ResearchProvider,
    SearchProvider,
)


@lru_cache(maxsize=1)
def get_docintel_provider() -> DocIntelProvider:
    settings = get_settings()
    if settings.PROVIDER_MODE == "azure" and settings.AZURE_DOCINTEL_ENDPOINT:
        from app.providers.azure import AzureDocIntelProvider
        return AzureDocIntelProvider(settings.AZURE_DOCINTEL_ENDPOINT, settings.AZURE_DOCINTEL_KEY)
    from app.providers.mock import MockDocIntelProvider
    return MockDocIntelProvider()


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    if settings.PROVIDER_MODE == "azure" and settings.AZURE_OPENAI_ENDPOINT:
        from app.providers.azure import AzureLLMProvider
        return AzureLLMProvider(
            settings.AZURE_OPENAI_ENDPOINT,
            settings.AZURE_OPENAI_API_KEY,
            settings.AZURE_OPENAI_DEPLOYMENT,
            settings.AZURE_EMBEDDING_DEPLOYMENT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            extract_deployment=settings.AZURE_OPENAI_DEPLOYMENT_EXTRACT,
            verifier_deployment=settings.AZURE_OPENAI_DEPLOYMENT_VERIFIER,
            embedding_api_key=settings.AZURE_EMBEDDING_API_KEY or None,
        )
    from app.providers.mock import MockLLMProvider
    return MockLLMProvider()


@lru_cache(maxsize=1)
def get_agent_provider() -> AgentProvider:
    settings = get_settings()
    if settings.PROVIDER_MODE == "azure" and settings.AZURE_OPENAI_ENDPOINT:
        from app.providers.azure import AzureAgentProvider
        return AzureAgentProvider(
            settings.AZURE_OPENAI_ENDPOINT,
            settings.AZURE_OPENAI_API_KEY,
            extract_deployment=settings.AZURE_OPENAI_DEPLOYMENT_EXTRACT,
            verifier_deployment=settings.AZURE_OPENAI_DEPLOYMENT_VERIFIER,
            router_deployment=settings.AZURE_OPENAI_DEPLOYMENT,
        )
    from app.providers.mock import MockAgentProvider
    return MockAgentProvider()


@lru_cache(maxsize=1)
def get_search_provider() -> SearchProvider:
    settings = get_settings()
    if settings.PROVIDER_MODE == "azure" and settings.AZURE_SEARCH_ENDPOINT:
        from app.providers.azure import AzureSearchProvider
        return AzureSearchProvider(settings.AZURE_SEARCH_ENDPOINT, settings.AZURE_SEARCH_KEY)
    from app.providers.mock import MockSearchProvider
    return MockSearchProvider()


@lru_cache(maxsize=1)
def get_research_provider() -> ResearchProvider:
    settings = get_settings()
    if settings.PROVIDER_MODE == "azure" and (
        settings.AZURE_DEEP_RESEARCH_API_KEY or settings.AZURE_OPENAI_API_KEY
    ):
        from app.providers.azure import AzureResearchProvider
        return AzureResearchProvider(
            settings.AZURE_DEEP_RESEARCH_ENDPOINT or settings.AZURE_OPENAI_ENDPOINT,
            settings.AZURE_DEEP_RESEARCH_API_KEY or settings.AZURE_OPENAI_API_KEY,
            deployment=settings.AZURE_DEEP_RESEARCH_DEPLOYMENT,
            region=settings.AZURE_DEEP_RESEARCH_REGION,
            api_version=settings.AZURE_DEEP_RESEARCH_API_VERSION,
        )
    from app.providers.mock import MockResearchProvider
    return MockResearchProvider()
