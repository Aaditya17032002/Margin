"""Colour-team review rounds.

The rounds a capture team runs before a proposal is sent — pink, red, gold,
white glove — and the sign-off that closes each one. They were happening in
email, which meant the record of who said a bid could proceed did not live
anywhere near the bid.

Two rules carry the weight.

**A round is opened against a version of the response.** A Red Team on draft 2
says nothing about draft 4, and the API refuses to open one against a response
that does not exist.

**A round is not closed while its must-fix findings are open** — unless the
person closing it writes down why. A deadline sometimes wins, and the honest
way to handle that is to let it win *on the record* rather than to make the
rule so soft that closing means nothing.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.core import permissions
from app.core.deps import CurrentUser, DbSession
from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck
from app.db.models.review import CHARTERS, ReviewFinding, ReviewRound
from app.pipeline import review_report
from app.schemas.resources import (
    ReviewCloseRequest,
    ReviewFindingCreate,
    ReviewFindingUpdate,
    ReviewRoundCreate,
)

router = APIRouter(tags=["reviews"])
logger = get_logger()

MUST_FIX = "must_fix"
OPEN = "open"


def _round_response(row: ReviewRound, findings: list[ReviewFinding]) -> dict:
    mine = [f for f in findings if f.round_id == row.id]
    return {
        "id": row.id,
        "analysisId": row.analysis_id,
        "colour": row.colour,
        "responseVersion": row.response_version,
        "charter": row.charter,
        "reviewers": list(row.reviewers or []),
        "status": row.status,
        "verdict": row.verdict,
        "note": row.note,
        "overrideReason": row.override_reason,
        "openedBy": row.opened_by,
        "openedAt": row.opened_at.isoformat() if row.opened_at else None,
        "closedBy": row.closed_by,
        "closedAt": row.closed_at.isoformat() if row.closed_at else None,
        "findings": [_finding_response(f) for f in mine],
        "openMustFix": sum(1 for f in mine if f.severity == MUST_FIX and f.state == OPEN),
        "history": row.history or [],
    }


def _finding_response(row: ReviewFinding) -> dict:
    return {
        "id": row.id,
        "roundId": row.round_id,
        "analysisId": row.analysis_id,
        "requirementId": row.requirement_id,
        "severity": row.severity,
        "text": row.text,
        "location": row.location or "",
        "state": row.state,
        "resolution": row.resolution,
        "raisedBy": row.raised_by,
        "raisedAt": row.raised_at.isoformat() if row.raised_at else None,
        "resolvedBy": row.resolved_by,
        "resolvedAt": row.resolved_at.isoformat() if row.resolved_at else None,
    }


async def _analysis(db, analysis_id: str, org_id: str) -> Analysis:
    row = (
        await db.execute(
            select(Analysis).where(
                Analysis.id == analysis_id, Analysis.org_id == org_id, Analysis.deleted_at.is_(None)
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    return row


def _event(at: datetime, event: str, detail: str) -> dict:
    return {"at": at.isoformat(), "event": event, "detail": detail}


@router.get("/analyses/{analysis_id}/reviews")
async def list_reviews(analysis_id: str, user: CurrentUser, db: DbSession):
    await _analysis(db, analysis_id, user.org_id)
    rounds = (
        await db.execute(
            select(ReviewRound)
            .where(ReviewRound.analysis_id == analysis_id, ReviewRound.org_id == user.org_id)
            .order_by(ReviewRound.opened_at.desc())
        )
    ).scalars().all()
    findings = (
        await db.execute(
            select(ReviewFinding).where(ReviewFinding.analysis_id == analysis_id)
        )
    ).scalars().all()
    return {
        "charters": CHARTERS,
        "rounds": [_round_response(row, list(findings)) for row in rounds],
    }


@router.post("/analyses/{analysis_id}/reviews", status_code=status.HTTP_201_CREATED)
async def open_round(analysis_id: str, body: ReviewRoundCreate, user: CurrentUser, db: DbSession):
    """Open a round against the current draft.

    Refused when no response is bound: a review round with nothing to review is
    a meeting, and the record of it would say a draft passed when no draft
    existed.
    """
    analysis = await _analysis(db, analysis_id, user.org_id)
    version = int((analysis.response or {}).get("version") or 0)
    if not version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "No response is bound to this analysis, so there is nothing to review. Upload "
                "the draft first."
            ),
        )

    now = datetime.now(UTC)
    row = ReviewRound(
        id=f"rev_{uuid.uuid4().hex[:12]}",
        analysis_id=analysis_id,
        org_id=user.org_id,
        colour=body.colour,
        response_version=version,
        # The charter is copied in rather than looked up, so a round opened
        # today still says what it was for after the defaults change.
        charter=(body.charter or CHARTERS.get(body.colour, "")).strip(),
        reviewers=list(body.reviewers or []),
        status="open",
        opened_by=user.id,
        opened_at=now,
        history=[_event(now, "opened", f"{body.colour} review opened against draft {version}.")],
    )
    db.add(row)
    await db.flush()
    logger.info("review_opened", analysis_id=analysis_id, colour=body.colour, version=version)
    return _round_response(row, [])


@router.post("/analyses/{analysis_id}/reviews/{round_id}/findings", status_code=status.HTTP_201_CREATED)
async def raise_finding(
    analysis_id: str, round_id: str, body: ReviewFindingCreate, user: CurrentUser, db: DbSession
):
    round_row = await _round(db, analysis_id, round_id, user.org_id)
    if round_row.status != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "That round is closed. Open a new one rather than adding to a round somebody "
                "has already signed off — the sign-off would then cover something it never saw."
            ),
        )

    now = datetime.now(UTC)
    finding = ReviewFinding(
        id=f"rf_{uuid.uuid4().hex[:12]}",
        round_id=round_id,
        analysis_id=analysis_id,
        org_id=user.org_id,
        requirement_id=body.requirement_id,
        severity=body.severity,
        text=body.text,
        location=body.location or "",
        state=OPEN,
        raised_by=user.id,
        raised_at=now,
    )
    db.add(finding)
    await db.flush()
    return _finding_response(finding)


@router.patch("/analyses/{analysis_id}/reviews/{round_id}/findings/{finding_id}")
async def resolve_finding(
    analysis_id: str,
    round_id: str,
    finding_id: str,
    body: ReviewFindingUpdate,
    user: CurrentUser,
    db: DbSession,
):
    """Fix, accept or reject a finding.

    Rejecting one needs a reason. A finding closed with no word about it is a
    finding the next round raises again, and the reviewer who raised it has no
    way to know it was considered.
    """
    finding = (
        await db.execute(
            select(ReviewFinding).where(
                ReviewFinding.id == finding_id,
                ReviewFinding.round_id == round_id,
                ReviewFinding.org_id == user.org_id,
            )
        )
    ).scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    update = body.model_dump(exclude_unset=True, by_alias=False)
    new_state = update.get("state")
    if new_state == "rejected" and not (update.get("resolution") or finding.resolution or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Rejecting a finding needs a reason. Without one the reviewer who raised it "
                "cannot tell whether it was considered, and the next round raises it again."
            ),
        )

    if "text" in update:
        finding.text = update["text"]
    if "severity" in update:
        finding.severity = update["severity"]
    if "location" in update:
        finding.location = update["location"]
    if "resolution" in update:
        finding.resolution = update["resolution"]
    if new_state:
        finding.state = new_state
        if new_state == OPEN:
            finding.resolved_by = None
            finding.resolved_at = None
        else:
            finding.resolved_by = user.id
            finding.resolved_at = datetime.now(UTC)
    await db.flush()
    return _finding_response(finding)


@router.post("/analyses/{analysis_id}/reviews/{round_id}/close")
async def close_round(
    analysis_id: str, round_id: str, body: ReviewCloseRequest, user: CurrentUser, db: DbSession
):
    """Sign the round off.

    A round with unresolved must-fix findings does not close on its own. It can
    be closed over them, because a real deadline sometimes wins — but that
    takes a written reason and is recorded as an override, so a clean pass and
    an overridden one can never be mistaken for each other later.
    """
    permissions.require(user.role, "sign_off_review")
    round_row = await _round(db, analysis_id, round_id, user.org_id)
    # Enforced apart from the role matrix because it depends on who opened the
    # round rather than on who is asking — and admins are not exempt.
    permissions.require_separation(
        actor_id=user.id, opened_by=round_row.opened_by, action="Signing off a review round"
    )
    if round_row.status == "closed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That round is already closed.")

    findings = (
        await db.execute(select(ReviewFinding).where(ReviewFinding.round_id == round_id))
    ).scalars().all()
    outstanding = [f for f in findings if f.severity == MUST_FIX and f.state == OPEN]

    if outstanding and not (body.override_reason or "").strip():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{len(outstanding)} must-fix finding(s) are still open. Resolve them, or close "
                "the round with a written reason — which is recorded as an override rather "
                "than as a pass."
            ),
        )

    now = datetime.now(UTC)
    round_row.status = "closed"
    round_row.verdict = body.verdict
    round_row.note = body.note
    round_row.closed_by = user.id
    round_row.closed_at = now
    if outstanding:
        round_row.override_reason = body.override_reason
    round_row.history = [
        *(round_row.history or []),
        _event(
            now,
            "closed",
            f"{body.verdict} by {user.id}"
            + (
                f", overriding {len(outstanding)} open must-fix finding(s): {body.override_reason}"
                if outstanding
                else ""
            ),
        ),
    ]
    await db.flush()
    logger.info(
        "review_closed",
        analysis_id=analysis_id,
        colour=round_row.colour,
        verdict=body.verdict,
        overridden=len(outstanding),
    )
    return _round_response(round_row, list(findings))


@router.get("/analyses/{analysis_id}/reviews/{round_id}/checklist")
async def white_glove_checklist(analysis_id: str, round_id: str, user: CurrentUser, db: DbSession):
    """What a white-glove round has to verify by hand.

    Every mechanical rule that came back `unverifiable` — fonts, margins,
    spacing, signatures, copies, binding, file formats. Margin can read those
    requirements and count nothing about them, because they are properties of
    the rendered file rather than of extracted text. This is the list of
    exactly what it could not see, which is what a production check is for.
    """
    round_row = await _round(db, analysis_id, round_id, user.org_id)
    checks = (
        await db.execute(
            select(ResponseCheck).where(
                ResponseCheck.analysis_id == analysis_id,
                ResponseCheck.response_version == round_row.response_version,
                ResponseCheck.verification == "mechanical",
                ResponseCheck.status == "unverifiable",
            )
        )
    ).scalars().all()
    requirements = {
        r.id: r
        for r in (
            await db.execute(select(Requirement).where(Requirement.analysis_id == analysis_id))
        )
        .scalars()
        .all()
    }
    return {
        "roundId": round_id,
        "responseVersion": round_row.response_version,
        "items": [
            {
                "checkId": check.id,
                "requirementId": check.requirement_id,
                "reference": (requirements.get(check.requirement_id).reference
                              if requirements.get(check.requirement_id) else ""),
                "requirement": (requirements.get(check.requirement_id).text
                                if requirements.get(check.requirement_id) else ""),
                "rule": check.rule,
                "whyNotChecked": check.detail,
                "stakes": (requirements.get(check.requirement_id).stakes
                           if requirements.get(check.requirement_id) else "scored"),
            }
            for check in checks
        ],
    }


async def _round(db, analysis_id: str, round_id: str, org_id: str) -> ReviewRound:
    row = (
        await db.execute(
            select(ReviewRound).where(
                ReviewRound.id == round_id,
                ReviewRound.analysis_id == analysis_id,
                ReviewRound.org_id == org_id,
            )
        )
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review round not found")
    return row


@router.get("/analyses/{analysis_id}/reviews/comparison")
async def compare_rounds(analysis_id: str, user: CurrentUser, db: DbSession):
    """The rounds read against each other rather than one at a time.

    Whether must-fix findings were fixed or merely accepted, what came back
    after somebody said it was fixed, what a closed round left open, and
    whether a sign-off still covers the draft about to be submitted. None of
    it is visible in a per-round view, which is why review programmes tend to
    produce three lists and no argument.
    """
    analysis = await _analysis(db, analysis_id, user.org_id)
    rounds = (
        await db.execute(
            select(ReviewRound).where(
                ReviewRound.analysis_id == analysis_id, ReviewRound.org_id == user.org_id
            )
        )
    ).scalars().all()
    findings = (
        await db.execute(select(ReviewFinding).where(ReviewFinding.analysis_id == analysis_id))
    ).scalars().all()
    return review_report.build(
        list(rounds),
        list(findings),
        current_version=int((analysis.response or {}).get("version") or 0),
    )
