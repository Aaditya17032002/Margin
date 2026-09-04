"""Shared Pydantic types — matching the frontend's types/index.ts exactly.

These are the source-of-truth contract types used in API responses.
Field names use camelCase via model_config to match the frontend.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# ── Config mixin ─────────────────────────────────────────────────────────

class CamelModel(BaseModel):
    """Base model that serialises to camelCase for the frontend."""
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
        ser_json_by_alias=True,
    )


# ── Enums ────────────────────────────────────────────────────────────────

class Stage(str, Enum):
    TRIAGE = "triage"
    ANALYZING = "analyzing"
    REVIEW = "review"
    DECIDED = "decided"


class GoNoGo(str, Enum):
    BID = "bid"
    NO_BID = "no-bid"
    WATCH = "watch"
    UNDECIDED = "undecided"


class Stakes(str, Enum):
    DISQUALIFYING = "disqualifying"
    SCORED = "scored"
    INFORMATIONAL = "informational"


class RequirementType(str, Enum):
    SHALL = "shall"
    SHOULD = "should"
    MAY = "may"


class MatrixStatus(str, Enum):
    UNASSIGNED = "unassigned"
    ASSIGNED = "assigned"
    DRAFTED = "drafted"
    IN_REVIEW = "in-review"
    COMPLETE = "complete"


class Role(str, Enum):
    ADMIN = "admin"
    REVIEWER = "reviewer"
    WRITER = "writer"
    VIEWER = "viewer"


class DocType(str, Enum):
    RFP = "RFP"
    RFI = "RFI"
    RFQ = "RFQ"
    IFB = "IFB"
    SOURCES_SOUGHT = "Sources Sought"
    BAA = "BAA"
    TASK_ORDER = "Task Order"


class AnalysisMode(str, Enum):
    QUICK_TRIAGE = "quick-triage"
    STANDARD = "standard"
    DEEP_RESEARCH = "deep-research"
    MATRIX_ONLY = "matrix-only"
    QA_ONLY = "qa-only"
    AMENDMENT_REFRESH = "amendment-refresh"
    RECOMPETE_COMPARE = "recompete-compare"


class FindingState(str, Enum):
    ANSWERED = "ANSWERED"
    SILENT = "SILENT"
    NEEDS_HUMAN = "NEEDS_HUMAN"


# ── Shared value objects ─────────────────────────────────────────────────

class BBox(CamelModel):
    x: float
    y: float
    w: float
    h: float


class Citation(CamelModel):
    id: str
    page: int
    #: Which document in the package. Page numbers restart per document, so a
    #: citation is only unambiguous with this beside it. Empty for analyses
    #: read before packages existed.
    document_id: str = ""
    document_name: str = ""
    section: str
    quote: str
    bbox: BBox
    #: The line range on that page the quote was resolved to, when it was
    #: resolved at all. The workspace highlights exactly these lines instead of
    #: guessing which ones the quote covers.
    lines: list[int] | None = None
    #: False when the quote could not be found in the extract. A reader is told
    #: rather than being scrolled to an arbitrary line and left to wonder.
    located: bool = False
    match_score: float = 0.0


class Finding(CamelModel):
    id: str
    label: str
    value: str
    detail: str | None = None
    confidence: float
    stakes: Stakes
    citation: Citation
    verified: bool | None = None
    flagged: bool | None = None


class Gate(CamelModel):
    id: str
    question: str
    answer: str
    met: bool | None = None
    citation: Citation | None = None
    weight: Literal["hard", "soft"]


class EvaluationFactor(CamelModel):
    id: str
    name: str
    weight: float
    method: str
    citation: Citation


class RiskItem(CamelModel):
    id: str
    title: str
    narrative: str
    severity: Literal["critical", "elevated", "moderate"]
    likelihood: Literal["likely", "possible", "unlikely"]
    mitigation: str
    citation: Citation


class SilentItem(CamelModel):
    id: str
    topic: str
    expectation: str
    consequence: str
    converted_to_question_id: str | None = Field(None, alias="convertedToQuestionId")


class KeyDate(CamelModel):
    id: str
    label: str
    at: str
    timezone: str
    kind: Literal[
        "intent-due",
        "questions-due",
        "answers-expected",
        "site-visit",
        "solution-review",
        "draft-review",
        "final-review",
        "proposal-due",
        "orals",
        "award",
        "start",
        "amendment",
    ]
    citation: Citation | None = None
    #: "document" when the solicitation stated this date, "derived" when Margin
    #: placed it around one that was stated. A reader must be able to tell.
    source: Literal["document", "derived"] = "document"


class Clin(CamelModel):
    id: str
    number: str
    description: str
    quantity: str
    ceiling: float | None = None


class DocumentPage(CamelModel):
    page: int
    heading: str | None = None
    lines: list[str]


class AmendmentChange(CamelModel):
    id: str
    kind: Literal["added", "changed", "removed"]
    area: str
    before: str | None = None
    after: str | None = None
    critical: bool | None = None


class AmendmentRecord(CamelModel):
    id: str
    label: str
    issued: str
    summary: str
    changes: list[AmendmentChange]


class VersionRecord(CamelModel):
    id: str
    label: str
    at: str
    author: str
    note: str


class ResearchSource(CamelModel):
    """One page a deep-research pass actually read."""

    url: str
    title: str = ""
    #: The host, shown next to the title. Whose site a claim came from is most
    #: of what tells a reader how much to trust it.
    site: str = ""


class ResearchClaim(CamelModel):
    """One paragraph of the research report, with the pages that back it.

    ``sources`` is empty when the search tool cited nothing for this
    paragraph. That is shown as-is: an unattributed claim borrowing the
    neighbouring paragraph's citation would be the same lie the whole
    research tab exists to prevent.
    """

    text: str
    sources: list[str] = []


class ExternalResearch(CamelModel):
    """What the open web said, kept separate from what the document says.

    A claim in here is never a citation: it has no page, no clause, and no
    standing against the solicitation. The workspace shows it under its own
    heading with its sources attached, so the distinction survives contact
    with a reader in a hurry.
    """

    status: str = "not_requested"  # completed | rate_limited | timeout | skipped | failed | not_requested
    detail: str = ""
    query: str = ""
    summary: str = ""
    sources: list[ResearchSource] = []
    #: The report broken into paragraphs, each carrying the URLs that back it.
    claims: list[ResearchClaim] = []
    at: str | None = None


class CoverageTotals(CamelModel):
    """Counted, never estimated. Every field is a tally of chunks or pages."""

    documents: int = 0
    empty_documents: int = 0
    pages: int = 0
    pages_scanned: int = 0
    pages_analysed: int = 0
    chunks: int = 0
    chunks_analysed: int = 0
    chunks_scanned: int = 0
    chunks_unreached: int = 0


class CoverageDocument(CamelModel):
    """One document's line in the ledger.

    `state` is the document's worst case, not its average: a document with a
    single unreached passage reads `unreached`, and one that produced no text
    at all reads `no_text` with a note saying so.
    """

    document_id: str = ""
    name: str = ""
    kind: str = "base"
    pages: int = 0
    state: str = "scanned"  # analysed | scanned | no_text | unreached
    pages_analysed: int = 0
    chunks: int = 0
    chunks_analysed: int = 0
    chunks_unreached: int = 0
    #: Contiguous page runs no pass reached, as [start, end] pairs.
    unreached_pages: list[list[int]] = []
    note: str = ""


class Coverage(CamelModel):
    """The proof behind "nothing was missed".

    Two numbers rather than one: everything the deterministic sweep visited
    (`pagesScanned`) and the narrower set a specialist actually reasoned over
    (`pagesAnalysed`). Collapsing them into a single percentage is what makes a
    coverage claim dishonest, so the shape refuses to.
    """

    at: str | None = None
    totals: CoverageTotals = CoverageTotals()
    documents: list[CoverageDocument] = []
    #: Specialist id → how many chunks it had in context.
    by_agent: dict[str, int] = {}
    #: Every passage reached and every document readable.
    complete: bool = False


class LedgerDelta(CamelModel):
    """What the last run did to the Requirement Ledger.

    A requirement the newest read stopped finding is not deleted, and this is
    where that shows up. `removedWithWork` names the ones somebody had already
    assigned or drafted against — those need a person, not a counter.
    """

    added: int = 0
    updated: int = 0
    unchanged: int = 0
    removed: int = 0
    removed_with_work: list[str] = []
    #: Answers already written against wording an amendment has since replaced.
    #: Named rather than counted: each one is a section somebody has to revisit.
    invalidated: list[str] = []


class ResponseSummary(CamelModel):
    """Counts from the last check of the bound response.

    `cleared` is deliberately smaller than the satisfied count: a mandatory
    requirement a rule or a model called satisfied is a recommendation until a
    person signs it, and conflating the two is how a response ships with a gap.
    """

    total: int = 0
    counts: dict[str, int] = {}
    cleared: int = 0
    awaiting_confirmation: int = 0
    blocking: int = 0
    blocking_references: list[str] = []


class ResponseBinding(CamelModel):
    """The draft response bound to this solicitation.

    A response is a separately versioned corpus compared *against* the
    solicitation, never mixed into it. Each draft is its own version so an
    earlier check stays answerable.
    """

    document_id: str = ""
    file_name: str = ""
    label: str = ""
    version: int = 0
    bound_at: str | None = None
    #: When it was last checked. Null between binding and the first check.
    at: str | None = None
    summary: ResponseSummary = ResponseSummary()


class ContradictionSummary(CamelModel):
    """What the last run found that cannot both be met.

    `found` is the count on the current read, not a running total: a
    contradiction an amendment resolved should stop being counted.
    """

    found: int = 0
    added: int = 0
    closed: int = 0


class FileNode(CamelModel):
    id: str
    name: str
    kind: Literal["folder", "file"]
    size: int | None = None
    modified: str | None = None
    children: list[FileNode] | None = None


# Self-referential model needs update_forward_refs
FileNode.model_rebuild()
