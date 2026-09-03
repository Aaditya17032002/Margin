"""Analysis Spec (v1.0) — Schema-first, fixed versioned framework (Sections A–M).

Every leaf field in this universal solicitation analysis framework resolves to:
- state: ANSWERED (+ citation + confidence) | SILENT | NEEDS_HUMAN
- stakes: disqualifying | scored | informational
- confidence: float (0.0 to 1.0)
- citation: Citation details (page, section, quote <= 15 words, bbox) or None if SILENT
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

from app.schemas.common import CamelModel, Citation, Stakes


class SpecFieldState(str, Enum):
    ANSWERED = "ANSWERED"
    SILENT = "SILENT"
    NEEDS_HUMAN = "NEEDS_HUMAN"


T = TypeVar("T")


class SpecLeafField(CamelModel, Generic[T]):
    """Every leaf item in the Analysis Spec is strictly typed and audited."""

    field_path: str = Field(..., description="Dot-path identification e.g. section_a.solicitation_number")
    label: str
    state: SpecFieldState = SpecFieldState.SILENT
    value: T | None = None
    detail: str | None = None
    stakes: Stakes = Stakes.INFORMATIONAL
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    citation: Citation | None = None
    verified: bool | None = None
    flagged: bool | None = None
    rationale_if_silent: str | None = None


# ── Section A: Solicitation Identity & Logistics ──────────────────────────
class SectionAIdentity(CamelModel):
    title: SpecLeafField[str]
    solicitation_number: SpecLeafField[str]
    issuing_agency: SpecLeafField[str]
    sub_agency: SpecLeafField[str]
    doc_type: SpecLeafField[str]
    naics_code: SpecLeafField[str]
    set_aside_designation: SpecLeafField[str]
    place_of_performance: SpecLeafField[str]
    estimated_ceiling_value: SpecLeafField[float]


# ── Section B: Key Dates & Deadlines ─────────────────────────────────────
class SectionBDates(CamelModel):
    questions_due: SpecLeafField[str]
    site_visit_mandatory: SpecLeafField[bool]
    site_visit_date: SpecLeafField[str]
    proposal_due_date: SpecLeafField[str]
    anticipated_award_date: SpecLeafField[str]
    period_of_performance_start: SpecLeafField[str]
    period_of_performance_duration: SpecLeafField[str]


# ── Section C: Scope & Core Requirements ──────────────────────────────────
class SectionCScope(CamelModel):
    statement_of_work_summary: SpecLeafField[str]
    primary_task_areas: SpecLeafField[list[str]]
    transition_in_window_days: SpecLeafField[int]
    transition_out_window_days: SpecLeafField[int]
    security_clearance_level: SpecLeafField[str]
    facility_clearance_required: SpecLeafField[bool]
    staffing_key_personnel_mandates: SpecLeafField[list[str]]
    deliverables_schedule: SpecLeafField[list[dict[str, Any]]]


# ── Section D: Agency Context & History ──────────────────────────────────
class SectionDContext(CamelModel):
    incumbent_contractor: SpecLeafField[str]
    prior_award_number: SpecLeafField[str]
    program_background: SpecLeafField[str]
    budget_source_type: SpecLeafField[str]


# ── Section E: Legal, Regulatory & Data Rights ───────────────────────────
class SectionELegal(CamelModel):
    applicable_regulations: SpecLeafField[list[str]]  # FAR/DFARS/agency clauses
    data_rights_clauses: SpecLeafField[str]
    cybersecurity_framework: SpecLeafField[str]  # e.g., CMMC Level 2, FedRAMP High, FERPA
    liquidated_damages: SpecLeafField[str]
    organizational_conflict_of_interest: SpecLeafField[str]
    subcontracting_plan_mandate: SpecLeafField[str]


# ── Section F: Mandatory Eligibility Gates ──────────────────────────────
class SectionFEligibility(CamelModel):
    sam_active_registration_gate: SpecLeafField[bool]
    facility_license_prior_to_bid: SpecLeafField[bool]
    mentor_protege_or_jv_rules: SpecLeafField[str]
    mandatory_certifications: SpecLeafField[list[str]]
    past_performance_recency_window_years: SpecLeafField[int]
    minimum_past_performance_projects: SpecLeafField[int]


# ── Section G: Evaluation Criteria & Scoring ─────────────────────────────
class SectionGEvaluation(CamelModel):
    basis_of_award: SpecLeafField[str]  # Best Value Tradeoff, LPTA, etc.
    technical_vs_price_relative_importance: SpecLeafField[str]
    evaluation_factors: SpecLeafField[list[dict[str, Any]]]
    oral_presentations_required: SpecLeafField[bool]
    sample_tasks_or_demonstrations: SpecLeafField[str]


# ── Section H: Submission Instructions & Formatting ─────────────────────
class SectionHSubmission(CamelModel):
    submission_method: SpecLeafField[str]  # Portal, email, physical
    volume_separation_rules: SpecLeafField[list[str]]
    page_limits_per_volume: SpecLeafField[dict[str, int]]
    font_and_margin_constraints: SpecLeafField[str]
    rejection_clauses_for_late_delivery: SpecLeafField[str]


# ── Section I: Technical Compliance Matrix ───────────────────────────────
class SectionIMatrix(CamelModel):
    shall_statements_count: SpecLeafField[int]
    mandatory_deliverables_count: SpecLeafField[int]
    identified_matrix_rows: SpecLeafField[list[dict[str, Any]]]


# ── Section J: Risk & Red-Flag Audit ─────────────────────────────────────
class SectionJRisk(CamelModel):
    unrealistic_schedules_detected: SpecLeafField[list[str]]
    ambiguous_clauses_detected: SpecLeafField[list[str]]
    cost_driver_hazards: SpecLeafField[list[str]]
    staffing_availability_risks: SpecLeafField[list[str]]


# ── Section K: Pricing Structure & CLINs ─────────────────────────────────
class SectionKPricing(CamelModel):
    contract_pricing_type: SpecLeafField[str]  # FFP, T&M, CPFF, IDIQ
    clins_identified: SpecLeafField[list[dict[str, Any]]]
    unpriced_options_present: SpecLeafField[bool]
    travel_and_odc_ceiling: SpecLeafField[float]


# ── Section L: Post-Award Administration ────────────────────────────────
class SectionLPostAward(CamelModel):
    invoicing_cadence: SpecLeafField[str]
    performance_metrics_sla: SpecLeafField[list[str]]
    quality_assurance_surveillance_plan: SpecLeafField[str]
    contract_modification_procedures: SpecLeafField[str]


# ── Section M: Clarifying Questions & Go/No-Go Recommendation ───────────
class SectionMStrategy(CamelModel):
    silent_items_converted_to_questions: SpecLeafField[list[dict[str, Any]]]
    ambiguity_questions: SpecLeafField[list[dict[str, Any]]]
    recommended_decision: SpecLeafField[str]  # bid | no-bid | watch | undecided
    go_nogo_confidence_score: SpecLeafField[float]
    executive_justification: SpecLeafField[str]


# ── Complete Universal Analysis Spec ─────────────────────────────────────
class UniversalAnalysisSpec(CamelModel):
    """The master Analysis Spec object versioned at 1.0."""

    spec_version: str = "1.0"
    identity: SectionAIdentity
    dates: SectionBDates
    scope: SectionCScope
    context: SectionDContext
    legal: SectionELegal
    eligibility: SectionFEligibility
    evaluation: SectionGEvaluation
    submission: SectionHSubmission
    matrix: SectionIMatrix
    risk: SectionJRisk
    pricing: SectionKPricing
    post_award: SectionLPostAward
    strategy: SectionMStrategy
