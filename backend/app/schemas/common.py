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
    at: str | None = None


class FileNode(CamelModel):
    id: str
    name: str
    kind: Literal["folder", "file"]
    size: int | None = None
    modified: str | None = None
    children: list[FileNode] | None = None


# Self-referential model needs update_forward_refs
FileNode.model_rebuild()
