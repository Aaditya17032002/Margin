"""Who owes what, and who changed what.

Two read-only views that exist because accountability is not a feature of any
single tab. A person's work is spread across every open pursuit, and the record
of who decided what is spread across three tables — neither is useful until it
is gathered in one place.

Both are derived on read. A stored worklist would need reconciling with the
requirements it points at, and a stored audit log would be a second version of
history that could disagree with the first.
"""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core import permissions
from app.core.deps import CurrentUser, DbSession
from app.core.logging import get_logger
from app.db.models.analysis import Analysis
from app.db.models.document import Document
from app.db.models.org import Org
from app.db.models.question import Question
from app.db.models.requirement import Requirement
from app.db.models.response_check import ResponseCheck
from app.pipeline import redaction, retention
from app.schemas.resources import LegalHoldRequest, RetentionApply, RetentionUpdate

router = APIRouter(tags=["governance"])
logger = get_logger()


@router.get("/work")
async def my_work(
    user: CurrentUser,
    db: DbSession,
    owner: str | None = Query(None, description="Whose work to list. Defaults to everyone's."),
):
    """Requirements someone owns, across every live pursuit.

    Ordered by the date the work is actually due, with anything overdue first
    and anything mandatory ahead of anything scored on the same day. A list
    ordered by analysis would make a person read all of them to find the one
    thing due tomorrow.
    """
    analyses = {
        row.id: row
        for row in (
            await db.execute(
                select(Analysis).where(
                    Analysis.org_id == user.org_id,
                    Analysis.deleted_at.is_(None),
                    Analysis.go_no_go != "no-bid",
                )
            )
        )
        .scalars()
        .all()
    }
    if not analyses:
        return {"items": [], "summary": {"total": 0, "overdue": 0, "unscheduled": 0}}

    query = select(Requirement).where(
        Requirement.org_id == user.org_id,
        Requirement.analysis_id.in_(list(analyses)),
        Requirement.state == "open",
        Requirement.status != "complete",
    )
    if owner:
        query = query.where(Requirement.owner == owner)
    else:
        query = query.where(Requirement.owner.is_not(None))

    rows = (await db.execute(query)).scalars().all()
    now = datetime.now(UTC)

    items = []
    for row in rows:
        analysis = analyses.get(row.analysis_id)
        overdue = bool(row.due_at and row.due_at < now)
        items.append(
            {
                "requirementId": row.id,
                "analysisId": row.analysis_id,
                "analysisTitle": analysis.title if analysis else "",
                "solicitationNumber": analysis.solicitation_number if analysis else "",
                "reference": row.reference,
                "requirement": row.text,
                "stakes": row.stakes,
                "verification": row.verification,
                "owner": row.owner,
                "status": row.status,
                "dueAt": row.due_at.isoformat() if row.due_at else None,
                "overdue": overdue,
                "responseLocation": row.response_location or "",
            }
        )

    # Overdue first, then by due date, then mandatory ahead of scored. A row
    # with no date sorts last: it is work nobody has committed to a day, which
    # is a different problem from work that is late.
    stakes_order = {"disqualifying": 0, "scored": 1, "informational": 2}
    items.sort(
        key=lambda item: (
            not item["overdue"],
            item["dueAt"] or "9999",
            stakes_order.get(item["stakes"], 3),
            item["reference"],
        )
    )
    return {
        "items": items,
        "summary": {
            "total": len(items),
            "overdue": sum(1 for item in items if item["overdue"]),
            "unscheduled": sum(1 for item in items if not item["dueAt"]),
        },
    }


@router.get("/analyses/{analysis_id}/audit")
async def audit_trail(analysis_id: str, user: CurrentUser, db: DbSession):
    """Everything that happened to this analysis, newest first.

    Assembled from the append-only histories the requirement ledger, the
    response checks and the Q&A already keep, plus the run versions and the
    amendment records. Nothing is written for this view — an audit log kept
    separately from the thing it describes is a second version of history, and
    the two eventually disagree.
    """
    analysis = (
        await db.execute(
            select(Analysis).where(
                Analysis.id == analysis_id,
                Analysis.org_id == user.org_id,
                Analysis.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    entries: list[dict] = []

    for version in analysis.versions or []:
        entries.append(
            {
                "at": version.get("at", ""),
                "scope": "run",
                "subject": version.get("label", "Analysis pass"),
                "event": "ran",
                "detail": version.get("note", ""),
                "actor": version.get("author", "Margin"),
            }
        )

    for record in analysis.amendments or []:
        entries.append(
            {
                "at": record.get("issued", ""),
                "scope": "amendment",
                "subject": record.get("label", "Amendment"),
                "event": "processed",
                "detail": record.get("summary", ""),
                "actor": "Margin",
            }
        )

    requirements = (
        await db.execute(select(Requirement).where(Requirement.analysis_id == analysis_id))
    ).scalars().all()
    by_id = {row.id: row for row in requirements}
    for row in requirements:
        for event in row.history or []:
            entries.append(
                {
                    "at": event.get("at", ""),
                    "scope": "requirement",
                    "subject": row.reference,
                    "event": event.get("event", ""),
                    "detail": event.get("detail", ""),
                    "actor": row.confirmed_by if event.get("event") == "edited" else "Margin",
                }
            )

    checks = (
        await db.execute(select(ResponseCheck).where(ResponseCheck.analysis_id == analysis_id))
    ).scalars().all()
    for check in checks:
        requirement = by_id.get(check.requirement_id)
        subject = requirement.reference if requirement else check.requirement_id
        for event in check.history or []:
            entries.append(
                {
                    "at": event.get("at", ""),
                    "scope": "response",
                    "subject": subject,
                    "event": event.get("event", ""),
                    "detail": event.get("detail", ""),
                    "actor": check.confirmed_by or "Margin",
                }
            )
        if check.confirmed_by and check.confirmed_at:
            entries.append(
                {
                    "at": check.confirmed_at.isoformat(),
                    "scope": "response",
                    "subject": subject,
                    "event": "signed off",
                    "detail": check.note or f"Accepted as {check.status}.",
                    "actor": check.confirmed_by,
                }
            )

    questions = (
        await db.execute(select(Question).where(Question.analysis_id == analysis_id))
    ).scalars().all()
    for question in questions:
        for event in question.history or []:
            entries.append(
                {
                    "at": event.get("at", ""),
                    "scope": "question",
                    "subject": question.text[:80],
                    "event": event.get("event", ""),
                    "detail": event.get("detail", ""),
                    "actor": "Margin",
                }
            )

    entries.sort(key=lambda entry: str(entry.get("at") or ""), reverse=True)
    return {"entries": entries, "total": len(entries)}


# ── The permission model, as data ────────────────────────────────────────


@router.get("/governance/permissions")
async def permission_matrix(user: CurrentUser):
    """Who can do what, and what the caller in particular can do.

    Shipped rather than documented. A permission model people cannot see is
    one they work around — usually by sharing an admin login, which is how a
    separation-of-duties control becomes decorative.
    """
    model = permissions.matrix()
    return {
        **model,
        "you": {
            "id": user.id,
            "role": user.role,
            "purpose": permissions.ROLE_PURPOSE.get(user.role, ""),
            "can": sorted(
                name for name in permissions.PERMISSIONS if permissions.allowed(user.role, name)
            ),
            "cannot": sorted(
                name
                for name in permissions.PERMISSIONS
                if not permissions.allowed(user.role, name)
            ),
        },
    }


# ── Retention ────────────────────────────────────────────────────────────


async def _org(db, org_id: str) -> Org:
    row = (await db.execute(select(Org).where(Org.id == org_id))).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return row


async def _live_analyses(db, org_id: str) -> list[Analysis]:
    return list(
        (
            await db.execute(
                select(Analysis).where(Analysis.org_id == org_id, Analysis.deleted_at.is_(None))
            )
        )
        .scalars()
        .all()
    )


@router.get("/governance/retention")
async def get_retention(user: CurrentUser, db: DbSession):
    """The policy, and exactly what it would dispose of today.

    The preview travels with the policy because the two are unreadable apart:
    "1095 days" means nothing until it is "and that is these eleven pursuits".
    """
    org = await _org(db, user.org_id)
    policy = retention.Policy.from_dict(org.retention)
    return {
        **retention.preview(await _live_analyses(db, user.org_id), policy),
        "classes": [
            {"name": name, "label": retention.CLASS_LABELS[name], "note": retention.CLASS_NOTES[name]}
            for name in retention.CLASSES
        ],
        "floorMinimumDays": retention.FLOOR_MINIMUM_DAYS,
        "canEdit": permissions.allowed(user.role, "manage_retention"),
    }


@router.put("/governance/retention")
async def set_retention(body: RetentionUpdate, user: CurrentUser, db: DbSession):
    """Change the policy.

    A policy that fails validation is refused with every problem at once
    rather than the first one: an admin editing four numbers should not have
    to submit four times to find out about all four.
    """
    permissions.require(user.role, "manage_retention")
    org = await _org(db, user.org_id)
    current = retention.Policy.from_dict(org.retention).as_dict()
    update = body.model_dump(exclude_unset=True, by_alias=False)
    proposed = retention.Policy.from_dict({**current, **update})

    problems = retention.validate(proposed)
    if proposed.enabled and problems:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=" ".join(problems),
        )

    org.retention = proposed.as_dict()
    await db.flush()
    logger.info("retention_policy_set", org_id=org.id, **org.retention)
    return {
        **retention.preview(await _live_analyses(db, user.org_id), proposed),
        "canEdit": True,
    }


@router.post("/governance/retention/apply")
async def apply_retention(body: RetentionApply, user: CurrentUser, db: DbSession):
    """Dispose of what the policy says is due, and nothing else.

    Three deliberate frictions. It never runs on read — a retention sweep that
    fires during a page refresh is how an audit trail disappears. It refuses
    when the count has moved since the preview, so nothing is destroyed that
    the caller did not see listed. And it disposes of documents only: the
    ledger, the verdicts, the sign-offs and the decision record are never in
    scope, on any policy.
    """
    permissions.require(user.role, "manage_retention")
    org = await _org(db, user.org_id)
    policy = retention.Policy.from_dict(org.retention)
    if not policy.enabled:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Retention is turned off for this workspace. Nothing was disposed of.",
        )

    analyses = await _live_analyses(db, user.org_id)
    plan = retention.preview(analyses, policy)
    due = plan["due"]
    if body.confirm != len(due):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"The preview you approved had {body.confirm} item(s); {len(due)} are due now. "
                "Nothing was disposed of — re-read the preview and confirm against it."
            ),
        )

    documents: dict[str, list[Document]] = {row.id: [] for row in analyses}
    for row in (
        await db.execute(
            select(Document).where(Document.analysis_id.in_([a.id for a in analyses] or [""]))
        )
    ).scalars().all():
        documents.setdefault(row.analysis_id, []).append(row)

    now = datetime.now(UTC)
    disposed: list[dict] = []
    for item in due:
        analysis_id = item["analysisId"]
        for document in documents.get(analysis_id, []):
            changed = _dispose(document, item["class"])
            if changed:
                disposed.append(
                    {
                        "analysisId": analysis_id,
                        "documentId": document.id,
                        "fileName": document.file_name,
                        "class": item["class"],
                        "detail": changed,
                    }
                )

    for analysis in analyses:
        touched = [d for d in disposed if d["analysisId"] == analysis.id]
        if not touched:
            continue
        analysis.versions = [
            *(analysis.versions or []),
            {
                "at": now.isoformat(),
                "label": "Retention disposal",
                "author": user.id,
                "note": (
                    f"{len(touched)} item(s) disposed of under the workspace retention policy"
                    + (f": {body.note}" if body.note.strip() else ".")
                ),
            },
        ]
    await db.flush()
    logger.info("retention_applied", org_id=org.id, disposed=len(disposed), by=user.id)
    return {"disposed": disposed, "count": len(disposed), "at": now.isoformat()}


def _dispose(document: Document, klass: str) -> str:
    """Remove one class of material from one document.

    The row survives. A document row carries the file name, the page count and
    the kind, and every citation in the matrix points at it — deleting the row
    would turn a cited matrix into a list of assertions, which is precisely
    what retention is not for.
    """
    if klass == "source_documents":
        if not document.storage_path:
            return ""
        path = Path(document.storage_path)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:  # noqa: BLE001
            logger.warning("retention_unlink_failed", path=str(path), error=str(exc))
        document.storage_path = None
        return "Uploaded file removed; the row, its name and its citations remain."
    if klass == "extracted_text":
        if not document.raw_text:
            return ""
        document.raw_text = None
        return "Extracted text removed; the package can no longer be re-analysed."
    if klass == "response_drafts":
        if document.doc_kind != "response" or not document.raw_text:
            return ""
        document.raw_text = None
        return "Draft response text removed; the verdicts recorded against it remain."
    return ""


@router.post("/analyses/{analysis_id}/legal-hold")
async def set_legal_hold(
    analysis_id: str, body: LegalHoldRequest, user: CurrentUser, db: DbSession
):
    """Put this pursuit out of reach of every retention timer, or let it back in.

    A hold needs a reason. One without a reason is indistinguishable from a
    hold somebody forgot to lift, and a workspace where everything is on
    permanent hold has no retention policy at all.
    """
    permissions.require(user.role, "manage_retention")
    analysis = (
        await db.execute(
            select(Analysis).where(
                Analysis.id == analysis_id,
                Analysis.org_id == user.org_id,
                Analysis.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")

    if body.hold and not body.reason.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A legal hold needs a reason. One without a reason cannot be told apart from a "
                "hold somebody forgot to lift."
            ),
        )

    now = datetime.now(UTC)
    analysis.legal_hold = body.hold
    analysis.legal_hold_reason = body.reason.strip() or None
    analysis.legal_hold_by = user.id if body.hold else None
    analysis.legal_hold_at = now if body.hold else None
    analysis.versions = [
        *(analysis.versions or []),
        {
            "at": now.isoformat(),
            "label": "Legal hold placed" if body.hold else "Legal hold lifted",
            "author": user.id,
            "note": body.reason.strip(),
        },
    ]
    await db.flush()
    logger.info("legal_hold_set", analysis_id=analysis_id, hold=body.hold, by=user.id)
    return {
        "analysisId": analysis_id,
        "legalHold": analysis.legal_hold,
        "reason": analysis.legal_hold_reason,
        "by": analysis.legal_hold_by,
        "at": analysis.legal_hold_at.isoformat() if analysis.legal_hold_at else None,
    }


# ── Personal data ────────────────────────────────────────────────────────


@router.get("/analyses/{analysis_id}/pii")
async def scan_pii(
    analysis_id: str,
    user: CurrentUser,
    db: DbSession,
    include_response: bool = Query(True, alias="includeResponse"),
):
    """What in this package looks like personal data, and where.

    Run before anything leaves the product. Detection is by pattern and
    deterministic, because a model that sometimes finds an SSN is worse than a
    regular expression that always finds that shape — the failure mode is
    invisible. Values are never returned in full; each finding shows a masked
    preview and the words either side of it.
    """
    documents = list(
        (
            await db.execute(
                select(Document).where(
                    Document.analysis_id == analysis_id, Document.org_id == user.org_id
                )
            )
        )
        .scalars()
        .all()
    )
    if not documents:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No documents are attached to this analysis.",
        )

    per_document = []
    totals: dict[str, int] = {}
    for document in documents:
        if document.doc_kind == "response" and not include_response:
            continue
        result = redaction.scan(document.raw_text or "")
        for kind, count in result.counts.items():
            totals[kind] = totals.get(kind, 0) + count
        per_document.append(
            {
                "documentId": document.id,
                "fileName": document.file_name,
                "kind": document.doc_kind,
                **result.as_dict(),
            }
        )

    return {
        "analysisId": analysis_id,
        "documents": per_document,
        "counts": totals,
        "total": sum(totals.values()),
        "kinds": [
            {"kind": d.kind, "label": d.label, "note": d.note} for d in redaction.DETECTORS
        ],
    }


# ── The record, as a file ────────────────────────────────────────────────


@router.get("/analyses/{analysis_id}/audit/export")
async def export_audit(analysis_id: str, user: CurrentUser, db: DbSession):
    """The audit trail as a spreadsheet.

    The same entries the view shows, in the order they happened — oldest
    first, because a file that will be read as a narrative is read forwards
    even though a screen is read backwards.
    """
    permissions.require(user.role, "export")
    trail = await audit_trail(analysis_id, user, db)
    entries = sorted(trail["entries"], key=lambda entry: str(entry.get("at") or ""))

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["When", "Scope", "Subject", "Event", "Detail", "Who"])
    for entry in entries:
        writer.writerow(
            [
                entry.get("at", ""),
                entry.get("scope", ""),
                entry.get("subject", ""),
                entry.get("event", ""),
                entry.get("detail", ""),
                entry.get("actor", ""),
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="audit-{analysis_id}.csv"',
        },
    )
