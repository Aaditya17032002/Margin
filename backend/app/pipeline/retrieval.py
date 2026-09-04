"""Choosing what each specialist reads.

A specialist cannot be handed a 600-page package, so something has to choose.
The old answer was "the first 70,000 characters", which chose by file order and
stopped around page 22. This chooses by relevance to the question that
specialist is actually asking.

Two things keep that honest. Retrieval is paired with the deterministic sweep,
which visits everything — so relevance decides depth, never coverage. And when
embeddings are unavailable, retrieval falls back to lexical scoring rather than
to document order, because "the first N chunks" wearing the name *retrieval* is
the failure this module was written to end.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from app.core.logging import get_logger
from app.pipeline.corpus import Corpus, CorpusChunk

logger = get_logger()

# What each specialist is looking for, in its own words. These are retrieval
# queries, not prompts: they are matched against the document, so they use the
# vocabulary a solicitation uses rather than the vocabulary we use internally.
AGENT_QUERIES: dict[str, list[str]] = {
    "intake": [
        "solicitation number, RFP number, issuing agency, contracting officer",
        "NAICS code, set-aside, small business, socioeconomic status",
        "place of performance, period of performance, contract type",
    ],
    "scope": [
        "scope of work, performance work statement, statement of objectives",
        "tasks, deliverables, milestones, reporting requirements",
        "transition, phase-in, phase-out, period of performance",
    ],
    "compliance": [
        "proposal instructions, submission requirements, format, page limit",
        "volume structure, required forms, certifications, signatures",
        "electronic submission, portal, file naming, late proposals",
    ],
    "eligibility": [
        "eligibility, minimum qualifications, experience requirements",
        "licensing, registration, SAM.gov, clearances, bonding, insurance",
        "past performance, references, similar projects, geographic restrictions",
    ],
    "evaluation": [
        "evaluation factors, subfactors, basis for award, relative importance",
        "technical approach, management approach, price evaluation, weighting",
        "adjectival ratings, best value, lowest price technically acceptable",
    ],
    "risk": [
        "key personnel, staffing, substitution, consent, availability",
        "intellectual property, data rights, liquidated damages, indemnification",
        "incumbent, transition risk, unclear scope, unusual terms",
    ],
    "pricing": [
        "pricing, cost proposal, CLIN, contract line item, unit price",
        "option years, labor categories, hourly rates, escalation",
        "cost realism, price analysis, invoicing, payment terms",
    ],
    "dates": [
        "questions due, deadline for questions, pre-proposal conference, site visit",
        "proposal due date, closing date, time and date for receipt",
        "oral presentations, demonstrations, anticipated award, start of performance",
    ],
    "qa": [
        "ambiguous, unclear, to be determined, not specified, reserved",
        "conflicting requirements, contradictions, inconsistencies",
        "silence on key terms, missing information",
    ],
}

# How much of the package each specialist gets. Wide enough to find what it is
# looking for, narrow enough that the model reads rather than skims.
DEFAULT_TOP_K = 40

_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    """a an and are as at be by for from in into is it of on or that the to with shall must will
    any all such other than which where when who whom this these those may should""".split()
)


@dataclass
class Retrieved:
    chunk: CorpusChunk
    score: float
    #: Which query pulled it in — useful when a specialist reports something odd.
    query: str


class CorpusRetriever:
    """Ranks corpus chunks against a query, by vector or by word.

    Embeddings are used when the run produced them. When it did not — no
    provider configured, an embedding call that failed — the lexical path takes
    over and says so in the logs. Both paths are deterministic given the same
    corpus, which is what lets the evaluation harness measure retrieval at all.
    """

    def __init__(self, corpus: Corpus, embeddings: list[list[float]] | None = None):
        self.corpus = corpus
        self.embeddings = embeddings if embeddings and len(embeddings) == len(corpus.chunks) else None
        self.mode = "vector" if self.embeddings else "lexical"
        if embeddings and not self.embeddings:
            logger.warning(
                "retrieval_embeddings_mismatched",
                chunks=len(corpus.chunks),
                embeddings=len(embeddings),
            )
        self._tokens: list[Counter] | None = None
        self._idf: dict[str, float] | None = None

    # ── Lexical index ────────────────────────────────────────────────────

    def _build_lexical(self) -> None:
        if self._tokens is not None:
            return
        self._tokens = [Counter(_terms(chunk.text)) for chunk in self.corpus.chunks]
        document_frequency: Counter = Counter()
        for counts in self._tokens:
            document_frequency.update(counts.keys())
        total = max(1, len(self._tokens))
        self._idf = {
            term: math.log(1 + total / (1 + freq)) for term, freq in document_frequency.items()
        }

    def _lexical_scores(self, query: str) -> list[float]:
        self._build_lexical()
        assert self._tokens is not None and self._idf is not None
        query_terms = set(_terms(query))
        scores = []
        for counts in self._tokens:
            length = sum(counts.values()) or 1
            score = sum(
                (counts[term] / length) * self._idf.get(term, 0.0) for term in query_terms if term in counts
            )
            scores.append(score)
        return scores

    # ── Retrieval ────────────────────────────────────────────────────────

    async def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[Retrieved]:
        if self.mode == "vector":
            scores = await self._vector_scores(query)
        else:
            scores = self._lexical_scores(query)

        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        out: list[Retrieved] = []
        for index in ranked[:top_k]:
            if scores[index] <= 0:
                break
            out.append(Retrieved(chunk=self.corpus.chunks[index], score=scores[index], query=query))
        return out

    async def _vector_scores(self, query: str) -> list[float]:
        from app.providers.factory import get_llm_provider

        try:
            vectors = await get_llm_provider().embed([query])
        except Exception as exc:  # noqa: BLE001 — a failed embed falls back, never fails the run
            logger.warning("retrieval_embed_failed", error=str(exc))
            return self._lexical_scores(query)
        if not vectors:
            return self._lexical_scores(query)
        return [_cosine(vectors[0], vector) for vector in (self.embeddings or [])]

    async def for_agent(self, agent_id: str, top_k: int = DEFAULT_TOP_K) -> list[Retrieved]:
        """The passages one specialist should read, merged across its queries.

        Each query contributes its best matches and the union is capped, so a
        specialist with three questions does not get three times the context of
        one with a single question.
        """
        queries = AGENT_QUERIES.get(agent_id)
        if not queries:
            # An agent with no queries still gets a fair share of the document
            # rather than nothing — but it is logged, because that is a gap in
            # the query table rather than a design.
            logger.warning("retrieval_no_queries", agent=agent_id)
            return [
                Retrieved(chunk=chunk, score=0.0, query="")
                for chunk in self.corpus.chunks[:top_k]
            ]

        per_query = max(4, top_k // len(queries))
        best: dict[int, Retrieved] = {}
        for query in queries:
            for hit in await self.search(query, top_k=per_query):
                existing = best.get(hit.chunk.chunk_index)
                if existing is None or hit.score > existing.score:
                    best[hit.chunk.chunk_index] = hit

        # Reading order, not score order: a specialist reasons better over
        # passages in the sequence the document states them.
        return sorted(best.values(), key=lambda r: r.chunk.chunk_index)[:top_k]


def _terms(text: str) -> list[str]:
    return [_fold(word) for word in _WORD.findall(text.lower()) if word not in _STOP and len(word) > 2]


def _fold(word: str) -> str:
    """Fold a word onto a crude stem so a query and a document can meet.

    A solicitation writes "Proposals shall not exceed 50 pages"; a specialist
    asks about "proposal page limits". Without folding, the two share no term
    and the passage scores zero — which is how a page limit on page 40 stays
    invisible. This is deliberately shallow: it collapses the plural and the
    handful of verb endings that separate the two vocabularies, and nothing
    more, so the index stays predictable and the harness can measure it.
    """
    for suffix, replacement in _SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: len(word) - len(suffix)] + replacement
    return word


#: Longest first — "ies" must be tried before "es", and "es" before "s".
_SUFFIXES: tuple[tuple[str, str], ...] = (
    ("ies", "y"),
    ("ing", ""),
    ("ses", "s"),
    ("xes", "x"),
    ("hes", "h"),
    ("es", "e"),
    ("s", ""),
    ("ed", ""),
)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
