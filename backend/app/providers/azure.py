"""Azure OpenAI providers — chat, embeddings, and specialist extraction."""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.pipeline.extract import extract_text
from app.pipeline.layout import LayoutExtractor
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

logger = get_logger()

_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)

SPECIALIST_INSTRUCTIONS: dict[str, str] = {
    "intake": (
        "Extract identity fields from this solicitation: document type (RFP/RFI/RFQ/IFB/etc), "
        "solicitation or RFx number, issuing agency, NAICS if present, set-aside status, "
        "place of performance, due date if stated. Only facts in the text."
    ),
    "scope": (
        "Extract what is being bought: core mission/PWS summary, period of performance, "
        "transition windows, key deliverables, places of performance. Quote the document."
    ),
    "compliance": (
        "Extract submission and compliance rules: page limits, volume structure, required forms, "
        "formatting, mandatory clauses, certifications. Each finding is one requirement."
    ),
    "eligibility": (
        "Extract eligibility gates stated in the document (SAM, set-aside, clearances, "
        "past performance, licensing, geographic restrictions). Do not guess whether the "
        "bidder meets them — report the requirement as written. If a gate is company-specific "
        "and not answered by the document, still record the requirement."
    ),
    "evaluation": (
        "Extract Section M / evaluation factors, weights (include the % in value when present), "
        "and evaluation method (LPTA, best value, etc.)."
    ),
    "risk": (
        "Extract capture risks that are grounded in the text: aggressive timelines, unusual IP, "
        "incumbent advantage, unclear scope, staffing mandates. Title in label, narrative in value."
    ),
    "pricing": (
        "Extract pricing instructions, CLIN structure, option years, and cost/price evaluation rules."
    ),
    "qa": (
        "Draft clarifying questions for silence, contradictions, or ambiguities in the solicitation. "
        "Do not invent questions the text already answers clearly."
    ),
}


def _is_new_max_tokens_model(deployment: str) -> bool:
    name = deployment.lower()
    return any(token in name for token in ("gpt-5", "o1", "o3", "o4"))


def _parse_json_object(text: str) -> dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        return {}
    match = _JSON_FENCE.search(raw)
    if match:
        raw = match.group(1).strip()
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            try:
                data = json.loads(raw[start : end + 1])
                return data if isinstance(data, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}


def _excerpt(chunks: list[ChunkResult], limit: int = 70_000) -> str:
    parts: list[str] = []
    used = 0
    for chunk in chunks:
        block = f"[p.{chunk.page} {chunk.section_path}]\n{chunk.text}\n"
        if used + len(block) > limit:
            break
        parts.append(block)
        used += len(block)
    return "\n".join(parts) if parts else ""


class LocalLayoutProvider(DocIntelProvider):
    """Layout from extracted text when Document Intelligence is not configured."""

    async def extract_layout(self, content: bytes, filename: str) -> LayoutResult:
        text = extract_text(content, filename)
        if not text.strip():
            text = content.decode("utf-8", errors="replace")
        return LayoutExtractor().extract_from_text(text, filename)


class AzureDocIntelProvider(DocIntelProvider):
    """Azure AI Document Intelligence — falls back to local text layout until wired."""

    def __init__(self, endpoint: str, key: str):
        self.endpoint = endpoint
        self.key = key

    async def extract_layout(self, content: bytes, filename: str) -> LayoutResult:
        logger.warning("docintel_not_wired_using_local_layout")
        return await LocalLayoutProvider().extract_layout(content, filename)


class AzureLLMProvider(LLMProvider):
    """Azure OpenAI chat + embeddings against named deployments."""

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
        embedding_dim: int = 1536,
        embedding_api_version: str = "2024-12-01-preview",
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.api_version = api_version
        self.deployment = deployment
        self.extract_deployment = extract_deployment or deployment
        self.verifier_deployment = verifier_deployment or deployment
        self.embedding_deployment = embedding_deployment
        self.embedding_api_key = embedding_api_key or api_key
        self.embedding_dim = embedding_dim
        self.embedding_api_version = embedding_api_version
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=20.0))

    def resolve_deployment(self, model: str | None = None) -> str:
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

    def _url(self, kind: str, deployment: str, *, api_version: str | None = None) -> str:
        version = api_version or self.api_version
        return (
            f"{self.endpoint}/openai/deployments/{deployment}/{kind}"
            f"?api-version={version}"
        )

    async def complete(self, messages: list[dict], *, model: str | None = None, **kwargs: Any) -> str:
        deployment = self.resolve_deployment(model)
        payload: dict[str, Any] = {"messages": messages}
        if kwargs.get("json"):
            payload["response_format"] = {"type": "json_object"}
        max_out = int(kwargs.get("max_tokens") or kwargs.get("max_completion_tokens") or 4096)
        if _is_new_max_tokens_model(deployment):
            payload["max_completion_tokens"] = max_out
        else:
            payload["max_tokens"] = max_out
            if "temperature" in kwargs:
                payload["temperature"] = kwargs["temperature"]
            elif kwargs.get("json"):
                payload["temperature"] = 0.1

        response = await self._client.post(
            self._url("chat/completions", deployment),
            headers={"api-key": self.api_key, "Content-Type": "application/json"},
            json=payload,
        )
        if response.status_code >= 400:
            logger.error("azure_chat_failed", status=response.status_code, body=response.text[:800], deployment=deployment)
            response.raise_for_status()
        data = response.json()
        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        return (message.get("content") or "").strip()

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        out: list[list[float]] = []
        batch_size = 64
        keys_to_try = [self.api_key]
        if self.embedding_api_key and self.embedding_api_key not in keys_to_try:
            keys_to_try.append(self.embedding_api_key)

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            last_error: str | None = None
            embedded = False
            for key in keys_to_try:
                response = await self._client.post(
                    self._url(
                        "embeddings",
                        self.embedding_deployment,
                        api_version=self.embedding_api_version,
                    ),
                    headers={"api-key": key, "Content-Type": "application/json"},
                    json={"input": batch, "dimensions": self.embedding_dim},
                )
                if response.status_code == 401:
                    last_error = response.text[:300]
                    continue
                if response.status_code >= 400:
                    logger.error("azure_embed_failed", status=response.status_code, body=response.text[:800])
                    response.raise_for_status()
                rows = sorted(response.json().get("data", []), key=lambda row: row.get("index", 0))
                out.extend(row["embedding"] for row in rows)
                embedded = True
                break
            if not embedded:
                raise RuntimeError(f"Azure embeddings unauthorized: {last_error}")
        return out


class AzureAgentProvider(AgentProvider):
    """Specialists that read the uploaded text via Azure chat completions."""

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        *,
        extract_deployment: str = "gpt-5.2",
        verifier_deployment: str = "gpt-5.2",
        router_deployment: str = "gpt-4o",
        llm: LLMProvider | None = None,
    ):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.extract_deployment = extract_deployment
        self.verifier_deployment = verifier_deployment
        self.router_deployment = router_deployment
        self._llm = llm

    def _llm_provider(self) -> LLMProvider:
        if self._llm is None:
            from app.providers.factory import get_llm_provider

            self._llm = get_llm_provider()
        return self._llm

    async def run_specialist(
        self, agent_id: str, schema_slice: dict, chunks: list[ChunkResult], **kwargs: Any
    ) -> AgentResult:
        events: list[dict] = [
            {"event": "agent_started", "agent": agent_id},
            {
                "event": "reasoning_tick",
                "agent": agent_id,
                "text": f"Reading the solicitation for {agent_id} findings.",
            },
        ]
        instruction = SPECIALIST_INSTRUCTIONS.get(
            agent_id, "Extract grounded findings from the solicitation text."
        )
        excerpt = _excerpt(chunks)
        if agent_id == "qa":
            findings = await self._extract_questions(instruction, excerpt)
        else:
            findings = await self._extract_findings(agent_id, instruction, excerpt, chunks)

        for finding in findings:
            events.append({"event": "finding_emitted", "agent": agent_id, "finding": finding})
        events.append({"event": "agent_completed", "agent": agent_id})
        return AgentResult(findings=findings, events=events)

    async def _extract_findings(
        self, agent_id: str, instruction: str, excerpt: str, chunks: list[ChunkResult]
    ) -> list[dict]:
        prompt = (
            "You are a government-capture analyst. Return JSON only.\n"
            f"Task: {instruction}\n"
            "Rules:\n"
            "- Use only the document excerpt. If a field is not in the text, omit it or mark value as SILENT.\n"
            "- Each finding needs a short verbatim quote from the excerpt.\n"
            "- stakes must be one of: informational, scored, disqualifying.\n"
            "- confidence is 0-1.\n"
            'Schema: {"findings":[{"label":str,"value":str,"detail":str,"confidence":number,'
            '"stakes":str,"citation":{"page":int,"section":str,"quote":str}}]}\n'
            f"Excerpt:\n{excerpt[:70000]}"
        )
        text = await self._llm_provider().complete(
            [
                {"role": "system", "content": "You extract grounded solicitation findings as JSON."},
                {"role": "user", "content": prompt},
            ],
            model="extract",
            json=True,
            max_tokens=3500,
        )
        data = _parse_json_object(text)
        items = data.get("findings") if isinstance(data.get("findings"), list) else []
        findings = []
        fallback_chunk = chunks[0] if chunks else None
        for item in items:
            if not isinstance(item, dict):
                continue
            citation_in = item.get("citation") if isinstance(item.get("citation"), dict) else {}
            quote = str(citation_in.get("quote") or item.get("value") or "")[:240]
            findings.append(
                {
                    "id": f"f_{uuid.uuid4().hex[:8]}",
                    "label": str(item.get("label") or "Finding")[:200],
                    "value": str(item.get("value") or "")[:2000],
                    "detail": (str(item.get("detail")) if item.get("detail") else None),
                    "confidence": _clamp_conf(item.get("confidence")),
                    "stakes": _stakes(item.get("stakes")),
                    "citation": {
                        "id": f"c_{uuid.uuid4().hex[:8]}",
                        "page": int(citation_in.get("page") or (fallback_chunk.page if fallback_chunk else 1)),
                        "section": str(citation_in.get("section") or (fallback_chunk.section_path if fallback_chunk else "")),
                        "quote": quote,
                        "bbox": (fallback_chunk.bbox if fallback_chunk else {"x": 0.05, "y": 0.1, "w": 0.9, "h": 0.06}),
                    },
                    "verified": None,
                    "flagged": False,
                }
            )
        logger.info("azure_specialist_complete", agent=agent_id, findings=len(findings))
        return findings

    async def _extract_questions(self, instruction: str, excerpt: str) -> list[dict]:
        prompt = (
            f"{instruction}\n"
            "Return JSON only: "
            '{"questions":[{"text":str,"rationale":str,"sourceKind":"silent|contradiction|ambiguity",'
            '"goNoGoImpact":bool,"citation":{"page":int,"section":str,"quote":str}}]}\n'
            "At most 8 questions. Every question must be justified by the excerpt.\n"
            f"Excerpt:\n{excerpt[:70000]}"
        )
        text = await self._llm_provider().complete(
            [
                {"role": "system", "content": "You draft solicitation Q&A as JSON."},
                {"role": "user", "content": prompt},
            ],
            model="extract",
            json=True,
            max_tokens=2500,
        )
        data = _parse_json_object(text)
        items = data.get("questions") if isinstance(data.get("questions"), list) else []
        questions = []
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            citation_in = item.get("citation") if isinstance(item.get("citation"), dict) else {}
            kind = str(item.get("sourceKind") or "silent")
            if kind not in {"silent", "contradiction", "ambiguity"}:
                kind = "silent"
            questions.append(
                {
                    "id": f"q_{uuid.uuid4().hex[:8]}",
                    "text": str(item.get("text") or "").strip(),
                    "rationale": str(item.get("rationale") or ""),
                    "sourceKind": kind,
                    "goNoGoImpact": bool(item.get("goNoGoImpact")),
                    "order": index,
                    "sent": False,
                    "citation": {
                        "id": f"c_{uuid.uuid4().hex[:8]}",
                        "page": int(citation_in.get("page") or 1),
                        "section": str(citation_in.get("section") or ""),
                        "quote": str(citation_in.get("quote") or "")[:240],
                        "bbox": {"x": 0.05, "y": 0.2, "w": 0.9, "h": 0.06},
                    },
                }
            )
        return [q for q in questions if q["text"]]

    async def verify(self, findings: list[dict], chunks: list[ChunkResult]) -> list[dict]:
        from app.agents.verifier import CitationVerifier

        return await CitationVerifier().verify_findings(findings, chunks)


def _clamp_conf(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.7
    return max(0.0, min(1.0, number))


def _stakes(value: Any) -> str:
    text = str(value or "informational").lower()
    if text in {"disqualifying", "scored", "informational"}:
        return text
    return "informational"


class AzureSearchProvider(SearchProvider):
    def __init__(self, endpoint: str, key: str):
        self.endpoint = endpoint
        self.key = key

    async def search(self, query: str, analysis_id: str, top_k: int = 10) -> list[RetrievalResult]:
        raise NotImplementedError("Configure AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY")


class AzureResearchProvider(ResearchProvider):
    """Azure Deep Research via the Responses API (o3-deep-research + web_search_preview).

    COMPLIANCE: `query` must be a generic derived string — never raw solicitation text.
    """

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        *,
        deployment: str = "o3-deep-research",
        region: str = "norwayeast",
        api_version: str = "2025-01-01-preview",
        poll_seconds: float = 8.0,
        max_wait_seconds: float = 900.0,
    ):
        self.endpoint = endpoint.rstrip("/") if endpoint else ""
        self.api_key = api_key
        self.deployment = deployment
        self.region = region
        self.api_version = api_version
        self.poll_seconds = poll_seconds
        self.max_wait_seconds = max_wait_seconds
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=20.0))

    def _responses_url(self, response_id: str | None = None) -> str:
        base = f"{self.endpoint}/openai/v1/responses"
        if response_id:
            return f"{base}/{response_id}"
        return base

    async def research(self, query: str) -> ResearchResult:
        if not self.endpoint or not self.api_key:
            logger.info("deep_research_skipped", reason="missing_endpoint")
            return ResearchResult(findings=[], sources=[], query_used=query)

        headers = {"api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "model": self.deployment,
            "background": True,
            "tools": [{"type": "web_search_preview"}],
            "input": query,
        }
        created = await self._client.post(self._responses_url(), headers=headers, json=payload)
        if created.status_code >= 400:
            logger.error("deep_research_create_failed", status=created.status_code, body=created.text[:800])
            created.raise_for_status()
        body = created.json()
        response_id = body.get("id")
        status = body.get("status") or "queued"
        logger.info("deep_research_started", response_id=response_id, status=status)

        elapsed = 0.0
        while status in {"queued", "in_progress", "incomplete"}:
            if elapsed >= self.max_wait_seconds:
                raise TimeoutError(f"o3-deep-research timed out after {self.max_wait_seconds}s ({response_id})")
            await asyncio.sleep(self.poll_seconds)
            elapsed += self.poll_seconds
            polled = await self._client.get(self._responses_url(response_id), headers=headers)
            if polled.status_code >= 400:
                logger.error("deep_research_poll_failed", status=polled.status_code, body=polled.text[:800])
                polled.raise_for_status()
            body = polled.json()
            status = body.get("status") or status
            logger.info("deep_research_poll", response_id=response_id, status=status, elapsed_s=int(elapsed))

        if status != "completed":
            logger.error("deep_research_failed", response_id=response_id, status=status, body=str(body)[:800])
            return ResearchResult(findings=[], sources=[], query_used=query)

        text, sources = _parse_responses_output(body)
        findings = []
        if text:
            findings.append(
                {
                    "id": f"dr_{uuid.uuid4().hex[:8]}",
                    "title": "External research (o3-deep-research)",
                    "summary": text[:8000],
                    "source": "azure-deep-research",
                }
            )
        logger.info("deep_research_complete", response_id=response_id, sources=len(sources), chars=len(text))
        return ResearchResult(findings=findings, sources=sources, query_used=query)


def _parse_responses_output(body: dict[str, Any]) -> tuple[str, list[dict]]:
    texts: list[str] = []
    sources: list[dict] = []
    seen: set[str] = set()

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            ntype = node.get("type")
            if ntype in {"output_text", "text"} and node.get("text"):
                texts.append(str(node["text"]))
            url = node.get("url") or node.get("uri")
            title = node.get("title") or node.get("name")
            if url and str(url) not in seen:
                seen.add(str(url))
                sources.append({"url": str(url), "title": str(title or url)})
            for annotation in node.get("annotations") or []:
                walk(annotation)
            for key in ("content", "output", "message"):
                if key in node:
                    walk(node[key])
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(body.get("output"))
    if not texts and body.get("output_text"):
        texts.append(str(body["output_text"]))
    return "\n\n".join(texts).strip(), sources


def build_llm_from_settings() -> AzureLLMProvider:
    settings = get_settings()
    return AzureLLMProvider(
        settings.AZURE_OPENAI_ENDPOINT,
        settings.AZURE_OPENAI_API_KEY,
        settings.AZURE_OPENAI_DEPLOYMENT,
        settings.AZURE_EMBEDDING_DEPLOYMENT,
        api_version=settings.AZURE_OPENAI_API_VERSION,
        extract_deployment=settings.AZURE_OPENAI_DEPLOYMENT_EXTRACT,
        verifier_deployment=settings.AZURE_OPENAI_DEPLOYMENT_VERIFIER,
        embedding_api_key=settings.AZURE_EMBEDDING_API_KEY or None,
        embedding_dim=settings.EMBEDDING_DIM,
        embedding_api_version=settings.AZURE_EMBEDDING_API_VERSION,
    )
