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
    #: The team's internal date for answering this, not the solicitation's.
    due_at: str | None = Field(None, alias="dueAt")


class MatrixRowResponse(CamelModel):
    """One requirement, shown as a matrix row.

    The first block is owned by the run and refreshed on every read of the
    package; the second is owned by whoever is answering the solicitation and
    a run never writes it. `key` is the identity that makes the difference
    possible — it is derived from the requirement's own words, so the row
    survives a re-read.
    """

    id: str
    analysis_id: str = Field(alias="analysisId")
    key: str = ""
    reference: str
    requirement: str
    type: str
    stakes: str
    #: The extraction category: obligation, instruction, limit, form,
    #: certification, volume.
    kind: str = "obligation"
    #: `mechanical` rules are checked by counting and never by a model;
    #: `substantive` ones have to be read.
    verification: str = "substantive"
    #: `open`, `superseded` by an amendment, or `removed` — never deleted.
    state: str = "open"
    #: Which passes found it: sweep, model, manual. Both passes agreeing is
    #: stronger than either alone.
    sources: list[str] = []

    owner: str | None
    response_location: str = Field(alias="responseLocation")
    status: str
    citation: Citation
    note: str | None = None
    #: Who cleared it. A mandatory requirement is never considered satisfied
    #: without a person's name against it.
    confirmed_by: str | None = Field(None, alias="confirmedBy")
    confirmed_at: str | None = Field(None, alias="confirmedAt")
    #: The team's internal date for answering this, not the solicitation's.
    due_at: str | None = Field(None, alias="dueAt")
    #: Append-only: {at, event, detail}.
    history: list[dict] = []


# ── Contradictions ───────────────────────────────────────────────────────

class ContradictionResolve(CamelModel):
    """Which requirement governs, and why.

    `disputed` is not a weaker `resolved`. It records that the document itself
    is contradictory and a question to the agency is the only way out — a
    different outcome, and the one most likely to move a deadline.
    """

    outcome: Literal["resolved", "disputed", "dismissed"] = "resolved"
    #: Required when resolving: the requirement that governs.
    governs_id: str | None = Field(None, alias="governsId")
    #: Six weeks from now this is the only record of why the team wrote to one
    #: clause and not the other.
    resolution: str


# ── Colour-team reviews ──────────────────────────────────────────────────

class ReviewRoundCreate(CamelModel):
    colour: Literal["pink", "red", "gold", "white_glove"] = "red"
    #: Left empty to take the default charter for that colour. A round whose
    #: reviewers disagree about its purpose produces findings nobody can act on.
    charter: str = ""
    reviewers: list[str] = []


class ReviewFindingCreate(CamelModel):
    text: str
    severity: Literal["must_fix", "should_fix", "consider"] = "should_fix"
    #: Where in the response — "Volume I, §3.2". Free text, because a reviewer
    #: reading a PDF describes a location the way they see it.
    location: str = ""
    #: The requirement it is about, when it is about one. This is what connects
    #: a review to the compliance matrix rather than leaving it a parallel list.
    requirement_id: str | None = Field(None, alias="requirementId")


class ReviewFindingUpdate(CamelModel):
    text: str | None = None
    severity: Literal["must_fix", "should_fix", "consider"] | None = None
    location: str | None = None
    state: Literal["open", "fixed", "accepted", "rejected"] | None = None
    #: Required to reject. A finding closed with no word about it is one the
    #: next round raises again.
    resolution: str | None = None


class ReviewCloseRequest(CamelModel):
    verdict: Literal["proceed", "proceed_with_fixes", "do_not_proceed"]
    note: str | None = None
    #: Required to close over unresolved must-fix findings, and recorded apart
    #: from `note` so a clean pass and an overridden one stay distinguishable.
    override_reason: str | None = Field(None, alias="overrideReason")


# ── Response traceability ────────────────────────────────────────────────

class ResponseCheckResponse(CamelModel):
    """One row of the trace: a solicitation clause, and what the response does
    about it.

    The first block is the solicitation half — clause, page, stakes — and the
    second is the response half. `decidedBy` says what kind of claim this is:
    `rule` was counted, `model` was read, `human` was signed. Collapsing those
    into one status is how a counted page limit and a model's opinion end up
    looking equally certain.
    """

    id: str
    analysis_id: str = Field(alias="analysisId")
    requirement_id: str = Field(alias="requirementId")
    response_version: int = Field(1, alias="responseVersion")

    reference: str = ""
    requirement: str = ""
    stakes: str = "scored"
    citation: dict = {}

    status: str = "unverifiable"
    verification: str = "substantive"
    decided_by: str = Field("rule", alias="decidedBy")
    #: Which mechanical rule fired, when one did.
    rule: str = ""
    detail: str = ""
    #: What is missing, in a sentence. Empty when nothing is.
    gap: str = ""
    risk: str = "low"
    owner: str | None = None
    #: Where in the response it was answered. `located: false` means the quote
    #: could not be found and the claim resting on it was downgraded.
    evidence: dict = {}
    #: A mandatory requirement a model called satisfied is a recommendation
    #: until a person signs it.
    needs_confirmation: bool = Field(False, alias="needsConfirmation")
    confirmed_by: str | None = Field(None, alias="confirmedBy")
    confirmed_at: str | None = Field(None, alias="confirmedAt")
    note: str | None = None
    history: list[dict] = []
    #: The chain, frozen when the check was written.
    lineage: dict = {}
    supersedes_id: str | None = Field(None, alias="supersedesId")
    #: A verdict carried from the previous draft because the passage did not
    #: change. A signature on a page nobody re-read is worth being able to see.
    carried_verdict: bool = Field(False, alias="carriedVerdict")


class ResponseCheckUpdate(CamelModel):
    """A person's verdict. It outranks both the rule and the model."""

    status: Literal["satisfied", "partial", "failed", "not_found", "unverifiable"] | None = None
    #: Signing off a mandatory requirement. The engine cannot do this itself.
    confirmed: bool | None = None
    note: str | None = None
    #: How you satisfied yourself. "Satisfied" with no basis is a name against
    #: an outcome; "counted 38 pages in the rendered PDF" is evidence, and only
    #: the second is worth anything in a debrief.
    basis: Literal[
        "read_the_document",
        "counted_in_the_file",
        "checked_with_the_agency",
        "team_knowledge",
        "prior_bid",
        "not_stated",
    ] = "not_stated"
    basis_detail: str = Field("", alias="basisDetail")


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
    #: The requirement this question is about, when it is about one. It is
    #: what lets the answer reach the clause rather than stopping at a list.
    requirement_id: str | None = Field(None, alias="requirementId")


class QuestionUpdate(CamelModel):
    text: str | None = None
    rationale: str | None = None
    go_no_go_impact: bool | None = Field(None, alias="goNoGoImpact")
    sent: bool | None = None
    requirement_id: str | None = Field(None, alias="requirementId")


class QuestionAnswer(CamelModel):
    """What the agency said back, and what it did to the requirement.

    The answer is stored verbatim — a Q&A answer is a contract document and the
    wording is the whole of it; a paraphrase is worth nothing in a dispute.

    `effect` is the part that makes this more than a notes field. An answer
    that merely explains a clause and an answer that rewrites it call for
    completely different work, and only the person reading it can say which
    this is.
    """

    answer: str
    #: Where it came from: "Amendment 0002", "Q&A set 1", an email date.
    source: str = ""
    #: `clarified` — the requirement stands and now has context.
    #: `amended` — the requirement is different now; supply `revisedRequirement`.
    #: `withdrawn` — it no longer applies.
    effect: Literal["clarified", "amended", "withdrawn"] = "clarified"
    #: The requirement as it now reads. Required when `effect` is `amended`:
    #: recording that a clause changed without saying how leaves the ledger
    #: knowing less than the person who filed it.
    revised_requirement: str | None = Field(None, alias="revisedRequirement")


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

    #: `draft`, `submitted`, `answered` or `withdrawn`. A question is not
    #: finished when it is sent — the answer is the point.
    status: str = "draft"
    submitted_at: str | None = Field(None, alias="submittedAt")
    answered_at: str | None = Field(None, alias="answeredAt")
    answer: str | None = None
    answer_source: str = Field("", alias="answerSource")
    requirement_id: str | None = Field(None, alias="requirementId")
    #: What the answer changed, when it changed anything.
    history: list[dict] = []


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
    format: Literal["DOCX", "PDF", "MD"] = "DOCX"
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
