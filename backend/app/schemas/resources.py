"""Resource schemas — matrix, questions, notifications, team, integrations,
templates, knowledge, reports, activity, preferences, deadlines, search."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from app.schemas.common import (
    CamelModel,
    Citation,
    FileNode,
    MatrixStatus,
    RequirementType,
    Stakes,
)


# ── Matrix ───────────────────────────────────────────────────────────────

class MatrixRowCreate(CamelModel):
    reference: str
    requirement: str
    type: RequirementType = RequirementType.SHALL
    stakes: Stakes = Stakes.SCORED
    owner: str | None = None
    response_location: str = Field("", alias="responseLocation")
    status: MatrixStatus = MatrixStatus.UNASSIGNED
    citation: Citation
    note: str | None = None


class MatrixRowUpdate(CamelModel):
    reference: str | None = None
    requirement: str | None = None
    type: RequirementType | None = None
    stakes: Stakes | None = None
    owner: str | None = None
    response_location: str | None = Field(None, alias="responseLocation")
    status: MatrixStatus | None = None
    note: str | None = None


class MatrixRowResponse(CamelModel):
    id: str
    analysis_id: str = Field(alias="analysisId")
    reference: str
    requirement: str
    type: str
    stakes: str
    owner: str | None
    response_location: str = Field(alias="responseLocation")
    status: str
    citation: Citation
    note: str | None = None


class BulkMatrixRequest(CamelModel):
    ids: list[str]
    owner: str | None = None
    status: MatrixStatus | None = None


# ── Questions ────────────────────────────────────────────────────────────

class QuestionCreate(CamelModel):
    text: str
    rationale: str
    source_kind: str = Field("manual", alias="sourceKind")
    go_no_go_impact: bool = Field(False, alias="goNoGoImpact")
    citation: Citation | None = None


class QuestionUpdate(CamelModel):
    text: str | None = None
    rationale: str | None = None
    go_no_go_impact: bool | None = Field(None, alias="goNoGoImpact")
    sent: bool | None = None


class QuestionResponse(CamelModel):
    id: str
    analysis_id: str = Field(alias="analysisId")
    text: str
    rationale: str
    source_kind: str = Field(alias="sourceKind")
    go_no_go_impact: bool = Field(alias="goNoGoImpact")
    order: int
    sent: bool
    citation: Citation | None = None


class ReorderRequest(CamelModel):
    ordered_ids: list[str] = Field(alias="orderedIds")


# ── Notifications ────────────────────────────────────────────────────────

class NotificationResponse(CamelModel):
    id: str
    at: str
    kind: str
    title: str
    body: str
    read: bool
    analysis_id: str | None = Field(None, alias="analysisId")
    href: str | None = None


class NotificationUpdate(CamelModel):
    read: bool | None = None


class NotificationCreate(CamelModel):
    kind: Literal["deadline", "review", "mention", "system", "export", "amendment"] = "system"
    title: str
    body: str = ""
    analysis_id: str | None = Field(None, alias="analysisId")
    href: str | None = None


# ── Team ─────────────────────────────────────────────────────────────────

class TeamMemberResponse(CamelModel):
    id: str
    name: str
    email: str
    role: str
    title: str
    status: str
    last_active: str = Field(alias="lastActive")
    initials_color: str = Field(alias="initialsColor")


class InviteRequest(CamelModel):
    name: str
    email: str
    role: str = "writer"
    title: str = ""


class TeamMemberUpdate(CamelModel):
    role: str | None = None
    title: str | None = None
    status: str | None = None


# ── Integrations ─────────────────────────────────────────────────────────

class IntegrationResponse(CamelModel):
    id: str
    name: str
    blurb: str
    connected: bool
    account: str | None = None
    connected_at: str | None = Field(None, alias="connectedAt")
    scopes: list[str]
    tree: list[FileNode]


class ConnectRequest(CamelModel):
    account: str | None = None
    code: str | None = None


class ImportRequest(CamelModel):
    file_ids: list[str] = Field(alias="fileIds")
    analysis_id: str | None = Field(None, alias="analysisId")


# ── Templates ────────────────────────────────────────────────────────────

class TemplateCreate(CamelModel):
    name: str
    kind: Literal["report", "boilerplate", "dpa"] = "report"
    description: str = ""
    sections: list[str] = []
    format: Literal["DOCX", "PDF", "MD"] = "DOCX"


class TemplateUpdate(CamelModel):
    name: str | None = None
    description: str | None = None
    sections: list[str] | None = None


class TemplateResponse(CamelModel):
    id: str
    name: str
    kind: str
    description: str
    sections: list[str]
    updated_at: str = Field(alias="updatedAt")
    usage_count: int = Field(alias="usageCount")
    format: str


# ── Knowledge ────────────────────────────────────────────────────────────

class KnowledgeCreate(CamelModel):
    title: str
    agency: str
    submitted_at: str = Field(alias="submittedAt")
    outcome: str = "pending"
    value: float = 0
    debrief: str = ""
    lessons: list[str] = []
    incumbent: str | None = None
    score_gap: str | None = Field(None, alias="scoreGap")


class KnowledgeUpdate(CamelModel):
    title: str | None = None
    outcome: str | None = None
    debrief: str | None = None
    lessons: list[str] | None = None


class KnowledgeResponse(CamelModel):
    id: str
    title: str
    agency: str
    submitted_at: str = Field(alias="submittedAt")
    outcome: str
    value: float
    debrief: str
    lessons: list[str]
    incumbent: str | None = None
    score_gap: str | None = Field(None, alias="scoreGap")


# ── Reports ──────────────────────────────────────────────────────────────

class ReportGenerateRequest(CamelModel):
    template_name: str = Field(alias="templateName")
    format: Literal["DOCX", "PDF"] = "DOCX"
    destination: Literal["download", "onedrive", "outlook"] = "download"
    idempotency_key: str | None = Field(None, alias="idempotencyKey")


class ReportResponse(CamelModel):
    id: str
    at: str
    analysis_id: str = Field(alias="analysisId")
    analysis_title: str = Field(alias="analysisTitle")
    template_name: str = Field(alias="templateName")
    format: str
    size: int
    destination: str
    status: str


# ── Activity ─────────────────────────────────────────────────────────────

class ActivityCreate(CamelModel):
    actor: str
    action: str
    target: str | None = None
    analysis_id: str | None = Field(None, alias="analysisId")


class ActivityResponse(CamelModel):
    id: str
    at: str
    actor: str
    action: str
    target: str | None = None
    analysis_id: str | None = Field(None, alias="analysisId")


# ── Preferences ──────────────────────────────────────────────────────────

class PrefsResponse(CamelModel):
    appearance: str
    density: str
    default_mode: str = Field(alias="defaultMode")
    shortcuts_enabled: bool = Field(alias="shortcutsEnabled")
    reduce_motion: bool = Field(alias="reduceMotion")
    margin_rail_pinned: bool = Field(alias="marginRailPinned")
    sidebar_collapsed: bool = Field(alias="sidebarCollapsed")
    coach_dismissed: bool = Field(alias="coachDismissed")
    notify: dict


class PrefsUpdate(CamelModel):
    appearance: str | None = None
    density: str | None = None
    default_mode: str | None = Field(None, alias="defaultMode")
    shortcuts_enabled: bool | None = Field(None, alias="shortcutsEnabled")
    reduce_motion: bool | None = Field(None, alias="reduceMotion")
    margin_rail_pinned: bool | None = Field(None, alias="marginRailPinned")
    sidebar_collapsed: bool | None = Field(None, alias="sidebarCollapsed")
    coach_dismissed: bool | None = Field(None, alias="coachDismissed")
    notify: dict | None = None


# ── Deadlines ────────────────────────────────────────────────────────────

class DeadlineResponse(CamelModel):
    id: str
    label: str
    at: str
    timezone: str
    kind: str
    source: str = "document"
    analysis_id: str = Field(alias="analysisId")
    analysis_title: str = Field(alias="analysisTitle")
    analysis_stage: str = Field("", alias="analysisStage")
    go_no_go: str = Field("", alias="goNoGo")


# ── Search ───────────────────────────────────────────────────────────────

class SearchResult(CamelModel):
    kind: Literal["analysis", "knowledge"]
    id: str
    title: str
    snippet: str
    score: float
