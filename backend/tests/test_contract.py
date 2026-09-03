"""Contract tests — assert response schemas match frontend TypeScript types.

These tests verify that the Pydantic schemas can produce the exact JSON shapes
the frontend expects, field by field.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.common import (
    AmendmentRecord,
    BBox,
    Citation,
    Clin,
    DocumentPage,
    EvaluationFactor,
    Finding,
    Gate,
    KeyDate,
    RiskItem,
    SilentItem,
    VersionRecord,
)
from app.schemas.analysis import AnalysisResponse, AnalysisListItem
from app.schemas.resources import (
    MatrixRowResponse,
    QuestionResponse,
    NotificationResponse,
    TeamMemberResponse,
    IntegrationResponse,
    TemplateResponse,
    KnowledgeResponse,
    ReportResponse,
    ActivityResponse,
    DeadlineResponse,
    SearchResult,
    PrefsResponse,
)


class TestCitationContract:
    def test_citation_fields(self):
        c = Citation(
            id="c_1", page=42, section="Section C.3",
            quote="shall provide", bbox=BBox(x=0.1, y=0.2, w=0.8, h=0.05),
        )
        d = c.model_dump(by_alias=True)
        assert "id" in d
        assert "page" in d
        assert "section" in d
        assert "quote" in d
        assert "bbox" in d
        assert d["bbox"]["x"] == 0.1


class TestFindingContract:
    def test_finding_fields(self):
        f = Finding(
            id="f_1", label="Test", value="Val",
            confidence=0.95, stakes="scored",
            citation=Citation(
                id="c_1", page=1, section="A",
                quote="q", bbox=BBox(x=0, y=0, w=1, h=1),
            ),
        )
        d = f.model_dump(by_alias=True)
        assert all(k in d for k in ["id", "label", "value", "confidence", "stakes", "citation"])


class TestAnalysisResponseContract:
    def test_has_all_frontend_fields(self):
        """Verify AnalysisResponse has every field from the frontend Analysis type."""
        frontend_fields = {
            "id", "title", "solicitationNumber", "agency", "subAgency", "docType",
            "mode", "stage", "goNoGo", "decisionNote", "createdAt", "updatedAt",
            "owner", "collaborators", "naics", "setAside", "placeOfPerformance",
            "estimatedValue", "pageCount", "fileName", "fileSize", "source", "tags",
            "summary", "identity", "scope", "legal", "eligibility", "pricing",
            "postAward", "gates", "evaluation", "risks", "silent", "dates", "clins",
            "amendments", "pages", "versions",
        }
        schema_fields = set()
        for name, field in AnalysisResponse.model_fields.items():
            alias = field.alias or name
            schema_fields.add(alias)

        missing = frontend_fields - schema_fields
        assert not missing, f"AnalysisResponse missing fields: {missing}"


class TestMatrixContract:
    def test_matrix_row_fields(self):
        frontend_fields = {"id", "analysisId", "reference", "requirement", "type", "stakes", "owner", "responseLocation", "status", "citation", "note"}
        schema_fields = set()
        for name, field in MatrixRowResponse.model_fields.items():
            alias = field.alias or name
            schema_fields.add(alias)
        missing = frontend_fields - schema_fields
        assert not missing, f"MatrixRowResponse missing fields: {missing}"


class TestNotificationContract:
    def test_notification_fields(self):
        frontend_fields = {"id", "at", "kind", "title", "body", "read", "analysisId", "href"}
        schema_fields = set()
        for name, field in NotificationResponse.model_fields.items():
            alias = field.alias or name
            schema_fields.add(alias)
        missing = frontend_fields - schema_fields
        assert not missing, f"NotificationResponse missing fields: {missing}"


class TestPrefsContract:
    def test_prefs_fields(self):
        frontend_fields = {
            "appearance", "density", "defaultMode", "shortcutsEnabled",
            "reduceMotion", "marginRailPinned", "sidebarCollapsed",
            "coachDismissed", "notify",
        }
        schema_fields = set()
        for name, field in PrefsResponse.model_fields.items():
            alias = field.alias or name
            schema_fields.add(alias)
        missing = frontend_fields - schema_fields
        assert not missing, f"PrefsResponse missing fields: {missing}"
