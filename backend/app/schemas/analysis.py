"""Analysis schemas — create, update, response matching frontend Analysis type."""

from __future__ import annotations

from app.schemas.common import (
    AmendmentRecord,
    AnalysisMode,
    CamelModel,
    Citation,
    Clin,
    Coverage,
    DocType,
    DocumentPage,
    EvaluationFactor,
    ExternalResearch,
    Finding,
    Gate,
    GoNoGo,
    KeyDate,
    LedgerDelta,
    RiskItem,
    SilentItem,
    Stage,
    Stakes,
    VersionRecord,
)
from pydantic import Field


class AnalysisCreate(CamelModel):
    title: str
    agency: str
    solicitation_number: str | None = Field(None, alias="solicitationNumber")
    doc_type: DocType | None = Field(DocType.RFP, alias="docType")
    mode: AnalysisMode
    file_name: str = Field(alias="fileName")
    file_size: int = Field(alias="fileSize")
    source: str = "upload"
    owner: str


class AnalysisUpdate(CamelModel):
    title: str | None = None
    agency: str | None = None
    solicitation_number: str | None = Field(None, alias="solicitationNumber")
    sub_agency: str | None = Field(None, alias="subAgency")
    doc_type: DocType | None = Field(None, alias="docType")
    mode: AnalysisMode | None = None
    stage: Stage | None = None
    go_no_go: GoNoGo | None = Field(None, alias="goNoGo")
    decision_note: str | None = Field(None, alias="decisionNote")
    naics: str | None = None
    set_aside: str | None = Field(None, alias="setAside")
    place_of_performance: str | None = Field(None, alias="placeOfPerformance")
    estimated_value: float | None = Field(None, alias="estimatedValue")
    tags: list[str] | None = None
    summary: str | None = None


class DecideRequest(CamelModel):
    decision: GoNoGo
    note: str | None = None


class RunRequest(CamelModel):
    mode: AnalysisMode | None = None
    idempotency_key: str | None = Field(None, alias="idempotencyKey")


class AnalysisResponse(CamelModel):
    id: str
    title: str
    solicitation_number: str = Field(alias="solicitationNumber")
    agency: str
    sub_agency: str | None = Field(None, alias="subAgency")
    doc_type: str = Field(alias="docType")
    mode: str
    stage: str
    go_no_go: str = Field(alias="goNoGo")
    decision_note: str | None = Field(None, alias="decisionNote")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    owner: str
    collaborators: list[str]
    naics: str
    set_aside: str = Field(alias="setAside")
    place_of_performance: str = Field(alias="placeOfPerformance")
    estimated_value: float = Field(alias="estimatedValue")
    page_count: int = Field(alias="pageCount")
    file_name: str = Field(alias="fileName")
    file_size: int = Field(alias="fileSize")
    source: str
    tags: list[str]
    summary: str
    identity: list[Finding]
    scope: list[Finding]
    legal: list[Finding]
    eligibility: list[Finding]
    pricing: list[Finding]
    post_award: list[Finding] = Field(alias="postAward")
    gates: list[Gate]
    evaluation: list[EvaluationFactor]
    risks: list[RiskItem]
    silent: list[SilentItem]
    dates: list[KeyDate]
    clins: list[Clin]
    amendments: list[AmendmentRecord]
    pages: list[DocumentPage]
    versions: list[VersionRecord]
    #: What was read and what was not. Empty on an analysis that has not run.
    coverage: Coverage = Coverage()
    #: What the last run changed in the Requirement Ledger.
    ledger: LedgerDelta = LedgerDelta()
    #: Only a deep-research pass fills this in; every other mode leaves it at
    #: its "not_requested" default.
    research: ExternalResearch = ExternalResearch()


class AnalysisListItem(AnalysisResponse):
    """The board shape.

    Everything the portfolio views read — findings, gates, risks, key dates —
    minus the document body, which is the one genuinely large array and is only
    ever rendered inside a single analysis. `pages` is sent empty; opening an
    analysis fetches the full record.
    """
