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
    kind: Literal["questions-due", "proposal-due", "site-visit", "award", "amendment", "start"]
    citation: Citation | None = None


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


class FileNode(CamelModel):
    id: str
    name: str
    kind: Literal["folder", "file"]
    size: int | None = None
    modified: str | None = None
    children: list[FileNode] | None = None


# Self-referential model needs update_forward_refs
FileNode.model_rebuild()
