"""Azure OpenAI providers — chat, embeddings, and specialist extraction."""

from __future__ import annotations

import asyncio
import json
import random
import re
import uuid
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger
from app.pipeline.anchor import CitationAnchor, resolve_citation
from app.workers.schedule import KINDS
from app.pipeline.extract import extract_pages
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

SCHEDULE_KINDS = KINDS

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
    "dates": (
        "Extract every date and deadline the solicitation states: notice of intent, "
        "written questions deadline, when answers are expected, site visits or "
        "pre-proposal conferences, the submission deadline, oral presentations or "
        "demonstrations, anticipated award, and the start of performance. Convert "
        "each to a calendar date. Do not infer a date the document does not give."
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


def _ground(
    anchor: CitationAnchor | None,
    quote: str,
    claimed: dict,
    fallback_chunk: ChunkResult | None,
) -> dict:
    """Turn what a model said about a citation into where the clause actually is."""
    fallback = (
        {
            "page": fallback_chunk.page,
            "section": fallback_chunk.section_path,
            "bbox": fallback_chunk.bbox,
        }
        if fallback_chunk
        else None
    )
    claimed_page = claimed.get("page")
    resolved = (
        resolve_citation(
            anchor,
            quote,
            claimed_page=int(claimed_page) if isinstance(claimed_page, (int, float, str)) and str(claimed_page).isdigit() else None,
            claimed_section=str(claimed.get("section") or ""),
            fallback=fallback,
        )
        if anchor is not None
        else {
            "page": int(fallback["page"]) if fallback else 1,
            "section": str(claimed.get("section") or (fallback["section"] if fallback else "")),
            "quote": quote,
            "bbox": (fallback["bbox"] if fallback else {"x": 0.06, "y": 0.04, "w": 0.88, "h": 0.05}),
            "lines": None,
            "located": False,
            "matchScore": 0.0,
        }
    )
    return {"id": f"c_{uuid.uuid4().hex[:8]}", **resolved}


class LocalLayoutProvider(DocIntelProvider):
    """Layout from extracted text when Document Intelligence is not configured."""

    async def extract_layout(self, content: bytes, filename: str) -> LayoutResult:
        pages = extract_pages(content, filename)
        if not any(page.strip() for page in pages):
            pages = [content.decode("utf-8", errors="replace")]
        return LayoutExtractor().extract_from_pages(pages, filename)


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
        # Citations are resolved against the document, not accepted from the
        # model. Without an anchor the extractor still runs, it just cannot
        # claim any of its citations are located.
        anchor: CitationAnchor | None = kwargs.get("anchor")
        if agent_id == "dates":
            findings = await self._extract_dates(instruction, excerpt, chunks, anchor)
        elif agent_id == "qa":
            findings = await self._extract_questions(instruction, excerpt, chunks, anchor)
        else:
            findings = await self._extract_findings(agent_id, instruction, excerpt, chunks, anchor)

        for finding in findings:
            events.append({"event": "finding_emitted", "agent": agent_id, "finding": finding})
        events.append({"event": "agent_completed", "agent": agent_id})
        return AgentResult(findings=findings, events=events)

    async def _extract_findings(
        self,
        agent_id: str,
        instruction: str,
        excerpt: str,
        chunks: list[ChunkResult],
        anchor: CitationAnchor | None = None,
    ) -> list[dict]:
        prompt = (
            "You are a government-capture analyst. Return JSON only.\n"
            f"Task: {instruction}\n"
            "Rules:\n"
            "- Use only the document excerpt. If a field is not in the text, omit it or mark value as SILENT.\n"
            "- citation.quote must be copied character for character from the excerpt. "
            "Do not paraphrase, join sentences, or fix typos — a quote that is not in the "
            "text is discarded and the finding loses its source.\n"
            "- Quote 1-3 whole sentences: enough to be unique in the document.\n"
            "- citation.page and citation.section must be the [p.N section] marker "
            "immediately above the quoted text.\n"
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
            quote = str(citation_in.get("quote") or item.get("value") or "")[:400]
            citation = _ground(anchor, quote, citation_in, fallback_chunk)
            findings.append(
                {
                    "id": f"f_{uuid.uuid4().hex[:8]}",
                    "label": str(item.get("label") or "Finding")[:200],
                    "value": str(item.get("value") or "")[:2000],
                    "detail": (str(item.get("detail")) if item.get("detail") else None),
                    "confidence": _clamp_conf(item.get("confidence")),
                    "stakes": _stakes(item.get("stakes")),
                    "citation": citation,
                    "verified": None,
                    "flagged": False,
                }
            )
        located = sum(1 for f in findings if f["citation"].get("located"))
        logger.info(
            "azure_specialist_complete",
            agent=agent_id,
            findings=len(findings),
            located=located,
            unlocated=len(findings) - located,
        )
        return findings

    async def _extract_dates(
        self,
        instruction: str,
        excerpt: str,
        chunks: list[ChunkResult],
        anchor: CitationAnchor | None = None,
    ) -> list[dict]:
        """Dates get their own pass because they need a different answer shape:
        a calendar date, not a sentence. Asking the identity agent for "due date
        if stated" produced prose that no calendar could read."""
        prompt = (
            f"{instruction}\n"
            "Return JSON only: "
            '{"dates":[{"label":str,"kind":str,"at":"YYYY-MM-DDTHH:MM:SS",'
            '"timezone":str,"citation":{"page":int,"section":str,"quote":str}}]}\n'
            "Rules:\n"
            "- kind is one of: " + ", ".join(SCHEDULE_KINDS) + ".\n"
            "- `at` must be a real calendar date. If the document gives a date with no "
            "time, use 00:00:00. If it gives no date at all for a stage, omit that stage "
            "entirely — never estimate one.\n"
            "- timezone is the one the document names (e.g. 'America/New_York'), else 'UTC'.\n"
            "- citation.quote must be copied character for character from the excerpt.\n"
            f"Excerpt:\n{excerpt[:70000]}"
        )
        text = await self._llm_provider().complete(
            [
                {"role": "system", "content": "You extract solicitation dates as JSON."},
                {"role": "user", "content": prompt},
            ],
            model="extract",
            json=True,
            max_tokens=2000,
        )
        data = _parse_json_object(text)
        items = data.get("dates") if isinstance(data.get("dates"), list) else []
        dates = []
        for item in items:
            if not isinstance(item, dict):
                continue
            citation_in = item.get("citation") if isinstance(item.get("citation"), dict) else {}
            dates.append(
                {
                    "label": str(item.get("label") or "")[:200],
                    "kind": str(item.get("kind") or ""),
                    "at": str(item.get("at") or ""),
                    "timezone": str(item.get("timezone") or "UTC")[:40],
                    "citation": _ground(
                        anchor,
                        str(citation_in.get("quote") or "")[:400],
                        citation_in,
                        chunks[0] if chunks else None,
                    ),
                }
            )
        logger.info("azure_specialist_complete", agent="dates", findings=len(dates))
        return dates

    async def _extract_questions(
        self,
        instruction: str,
        excerpt: str,
        chunks: list[ChunkResult],
        anchor: CitationAnchor | None = None,
    ) -> list[dict]:
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
                    "citation": _ground(
                        anchor,
                        str(citation_in.get("quote") or "")[:400],
                        citation_in,
                        chunks[0] if chunks else None,
                    ),
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
        max_attempts: int = 3,
        retry_base_seconds: float = 20.0,
    ):
        self.endpoint = endpoint.rstrip("/") if endpoint else ""
        self.api_key = api_key
        self.deployment = deployment
        self.region = region
        self.api_version = api_version
        self.poll_seconds = poll_seconds
        self.max_wait_seconds = max_wait_seconds
        self.max_attempts = max(1, max_attempts)
        self.retry_base_seconds = retry_base_seconds
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=20.0))

    def _responses_url(self, response_id: str | None = None) -> str:
        base = f"{self.endpoint}/openai/v1/responses"
        if response_id:
            return f"{base}/{response_id}"
        return base

    async def research(self, query: str) -> ResearchResult:
        """Run one deep-research pass, retrying the whole job through a rate limit.

        The deployment is a shared, capacity-limited resource, and a rejection
        arrives two ways: a 429 on the request, or — more often — an accepted
        background job that comes back ``failed`` with ``rate_limit_exceeded``
        minutes later. Both are the same thing and both are worth waiting out,
        because the alternative is a deep-research run that silently produces
        no research at all.
        """
        if not self.endpoint or not self.api_key:
            logger.info("deep_research_skipped", reason="missing_endpoint")
            return ResearchResult(
                findings=[], sources=[], query_used=query,
                status="skipped", detail="Deep research is not configured for this workspace.",
            )

        last = ResearchResult(query_used=query, status="failed", detail="No attempt completed.")
        for attempt in range(1, self.max_attempts + 1):
            outcome = await self._attempt(query, attempt)
            if outcome.status == "completed" or outcome.status not in RETRYABLE_RESEARCH_STATUSES:
                return outcome
            last = outcome
            if attempt < self.max_attempts:
                delay = outcome_retry_delay(outcome, self.retry_base_seconds, attempt)
                logger.warning(
                    "deep_research_retrying",
                    attempt=attempt,
                    of=self.max_attempts,
                    status=outcome.status,
                    sleep_s=round(delay),
                )
                await asyncio.sleep(delay)

        logger.error("deep_research_exhausted", attempts=self.max_attempts, status=last.status)
        return last

    async def _attempt(self, query: str, attempt: int) -> ResearchResult:
        headers = {"api-key": self.api_key, "Content-Type": "application/json"}
        payload = {
            "model": self.deployment,
            "background": True,
            "tools": [{"type": "web_search_preview"}],
            "input": query,
        }
        try:
            created = await self._client.post(self._responses_url(), headers=headers, json=payload)
        except httpx.HTTPError as exc:
            logger.warning("deep_research_create_error", attempt=attempt, error=str(exc))
            return ResearchResult(query_used=query, status="failed", detail=str(exc)[:300])

        if created.status_code == 429:
            retry_after = _retry_after(created.headers)
            logger.warning("deep_research_rate_limited", attempt=attempt, retry_after=retry_after)
            return ResearchResult(
                query_used=query,
                status="rate_limited",
                detail=f"retry-after={retry_after}" if retry_after else "429 on create",
            )
        if created.status_code >= 400:
            logger.error(
                "deep_research_create_failed",
                attempt=attempt,
                status=created.status_code,
                body=created.text[:800],
            )
            # 5xx is the service having a bad minute; 4xx is our request.
            status = "failed" if created.status_code < 500 else "rate_limited"
            return ResearchResult(query_used=query, status=status, detail=created.text[:300])

        body = created.json()
        response_id = body.get("id")
        status = body.get("status") or "queued"
        logger.info("deep_research_started", response_id=response_id, status=status, attempt=attempt)

        elapsed = 0.0
        while status in {"queued", "in_progress", "incomplete"}:
            if elapsed >= self.max_wait_seconds:
                logger.error("deep_research_timeout", response_id=response_id, waited_s=int(elapsed))
                return ResearchResult(
                    query_used=query,
                    status="timeout",
                    detail=f"No answer after {int(self.max_wait_seconds)}s.",
                )
            await asyncio.sleep(self.poll_seconds)
            elapsed += self.poll_seconds
            try:
                polled = await self._client.get(self._responses_url(response_id), headers=headers)
            except httpx.HTTPError as exc:
                logger.warning("deep_research_poll_error", response_id=response_id, error=str(exc))
                continue
            if polled.status_code >= 400:
                logger.error(
                    "deep_research_poll_failed", status=polled.status_code, body=polled.text[:800]
                )
                return ResearchResult(query_used=query, status="failed", detail=polled.text[:300])
            body = polled.json()
            status = body.get("status") or status
            logger.info("deep_research_poll", response_id=response_id, status=status, elapsed_s=int(elapsed))

        if status != "completed":
            error = body.get("error") if isinstance(body.get("error"), dict) else {}
            code = str(error.get("code") or "")
            message = str(error.get("message") or "")[:300]
            logger.error(
                "deep_research_failed",
                response_id=response_id,
                status=status,
                code=code,
                message=message,
            )
            return ResearchResult(
                query_used=query,
                status="rate_limited" if code in RETRYABLE_ERROR_CODES else "failed",
                detail=message or code or status,
            )

        text, sources, claims = _parse_responses_output(body)
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
        attributed = sum(1 for c in claims if c["sources"])
        logger.info(
            "deep_research_complete",
            response_id=response_id,
            sources=len(sources),
            chars=len(text),
            claims=len(claims),
            attributed=attributed,
        )
        return ResearchResult(
            findings=findings,
            sources=sources,
            claims=claims,
            query_used=query,
            status="completed",
        )


RETRYABLE_RESEARCH_STATUSES = {"rate_limited"}
RETRYABLE_ERROR_CODES = {"rate_limit_exceeded", "server_error", "service_unavailable"}


def _retry_after(headers: Any) -> float | None:
    for key in ("retry-after", "x-ratelimit-reset-requests", "retry-after-ms"):
        raw = headers.get(key)
        if not raw:
            continue
        try:
            value = float(str(raw).rstrip("smSM"))
        except ValueError:
            continue
        return value / 1000 if key.endswith("-ms") else value
    return None


def outcome_retry_delay(outcome: ResearchResult, base: float, attempt: int) -> float:
    """How long to wait before trying the deployment again.

    Honours a Retry-After the service gave us; otherwise backs off
    exponentially with jitter, so several analyses queued at once do not all
    come back and collide on the same second.
    """
    detail = outcome.detail or ""
    if detail.startswith("retry-after="):
        try:
            return max(1.0, min(300.0, float(detail.split("=", 1)[1])))
        except ValueError:
            pass
    return min(300.0, base * (2 ** (attempt - 1))) * (0.8 + random.random() * 0.4)


def _parse_responses_output(body: dict[str, Any]) -> tuple[str, list[dict], list[dict]]:
    """Pull the report, its sources, and which source backs which paragraph.

    The Responses API attaches ``url_citation`` annotations to each block of
    output text, carrying the character range of the sentence they support.
    That is the honest basis for per-claim attribution: it comes from the
    search tool recording what it actually read, not from asking the model
    afterwards which page it was thinking of.

    Returns ``(report, sources, claims)`` where a claim is one paragraph and
    the URLs whose citation spans fall inside it. A paragraph with no spans
    gets an empty list, and the workspace says so rather than borrowing a
    neighbour's source.
    """
    blocks: list[tuple[str, list[dict]]] = []
    sources: list[dict] = []
    seen: set[str] = set()

    def remember(url: Any, title: Any) -> None:
        if not url or str(url) in seen:
            return
        seen.add(str(url))
        sources.append({"url": str(url), "title": str(title or url)})

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            annotations = [a for a in (node.get("annotations") or []) if isinstance(a, dict)]
            if node.get("type") in {"output_text", "text"} and node.get("text"):
                blocks.append((str(node["text"]), annotations))
            remember(node.get("url") or node.get("uri"), node.get("title") or node.get("name"))
            for annotation in annotations:
                walk(annotation)
            for key in ("content", "output", "message"):
                if key in node:
                    walk(node[key])
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(body.get("output"))
    if not blocks and body.get("output_text"):
        blocks.append((str(body["output_text"]), []))

    # Stitch the blocks into one report while keeping every annotation's range
    # valid against the stitched text.
    separator = "\n\n"
    parts: list[str] = []
    spans: list[tuple[int, int, str]] = []
    cursor = 0
    for text, annotations in blocks:
        for annotation in annotations:
            url = annotation.get("url") or annotation.get("uri")
            if not url:
                continue
            start = annotation.get("start_index")
            end = annotation.get("end_index")
            if not isinstance(start, int) or not isinstance(end, int) or end <= start:
                continue
            spans.append((cursor + start, cursor + end, str(url)))
        parts.append(text)
        cursor += len(text) + len(separator)

    report = separator.join(parts).strip()
    return report, sources, _claims_from_spans(separator.join(parts), spans)


def _claims_from_spans(report: str, spans: list[tuple[int, int, str]]) -> list[dict]:
    """Split the report into paragraphs and give each one the sources it cites."""
    if not report.strip():
        return []

    claims: list[dict] = []
    offset = 0
    for paragraph in re.split(r"\n{2,}", report):
        start, end = offset, offset + len(paragraph)
        offset = end + 2
        body = paragraph.strip()
        if not body:
            continue
        cited: list[str] = []
        for span_start, span_end, url in spans:
            # Any overlap counts: a citation often marks the sentence it
            # supports, which can straddle the paragraph break in the source
            # text even though it reads as belonging to one of them.
            if span_start < end and span_end > start and url not in cited:
                cited.append(url)
        claims.append({"text": body, "sources": cited})
    return claims


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
