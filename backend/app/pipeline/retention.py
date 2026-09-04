"""How long things are kept, and what "deleted" is allowed to mean.

Every organisation running federal or municipal work has a retention
obligation, and most of them satisfy it with a folder nobody empties. The
reason is not laziness: deleting the wrong thing during a protest window is
career-ending, so nobody deletes anything, and the org accumulates a decade of
other people's personal data in a bucket.

The way out is not a shorter timer. It is being precise about *what* is being
disposed of, so that disposal stops being frightening.

**Retention disposes of documents, not of the record.** The source PDFs, the
extracted text, the draft responses — those age out. The requirement ledger,
the verdicts, who signed off which round, the decision record and its evidence
do not, ever, on any policy. What was decided and on what basis is the thing an
auditor asks for, it is small, and no plausible obligation is served by
destroying it.

**Nothing in a live pursuit is eligible.** A policy applies only once a pursuit
is settled — decided, or dropped — and the clock runs from the last thing that
happened to it rather than from the day it was created. A pursuit somebody
touched last week is not four hundred days old just because it opened then.

**A floor nothing can go below.** ``minimum_hold_days`` is a second lock on the
same door: a policy edited in a hurry cannot dispose of last month's work, and
lowering the floor is an admin action that says so out loud.

**A legal hold beats every timer.** One flag on an analysis and it is out of
scope until the flag comes off, whatever the policy says.

Nothing here deletes. It computes what *would* go and says why, and disposal is
a separate, explicit call — because a retention sweep that runs on read is how
an audit trail disappears during a page refresh.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.core.logging import get_logger

logger = get_logger()

#: What can be disposed of. Deliberately short, and deliberately not
#: extensible from the API: adding "verdicts" to this tuple is a decision to
#: destroy the record, and it should take a code review rather than a form.
CLASSES = ("source_documents", "extracted_text", "response_drafts")

CLASS_LABELS = {
    "source_documents": "Uploaded files",
    "extracted_text": "Extracted text",
    "response_drafts": "Draft responses",
}

CLASS_NOTES = {
    "source_documents": (
        "The original PDFs and attachments as uploaded. Citations keep the document name, "
        "page and quote, so the matrix still reads after the file is gone."
    ),
    "extracted_text": (
        "The text Margin read the package from. Removing it means the package cannot be "
        "re-analysed, so it is usually held longer than the files themselves."
    ),
    "response_drafts": (
        "Superseded drafts of the response. The verdicts against each draft survive — what "
        "goes is the draft body, not the record of what was checked in it."
    ),
}

#: Never disposed of, on any policy. Stated as data so a settings page can show
#: it: a promise nobody can see is one nobody believes.
NEVER_DISPOSED = (
    "The requirement ledger and its history",
    "Verification verdicts and who recorded them",
    "Review rounds, findings and sign-offs",
    "Questions to the agency and their answers",
    "The decision record and the evidence it was made on",
    "The audit trail",
)

#: A pursuit is only eligible once it has stopped moving.
SETTLED_STAGES = ("decided",)

#: Below this, the floor is not a floor. Chosen to cover the usual GAO protest
#: window with room either side; a shorter hold is a decision to dispose of
#: material while somebody can still ask for it.
FLOOR_MINIMUM_DAYS = 100

DEFAULT_POLICY = {
    "enabled": False,
    "source_documents_days": 1095,
    "extracted_text_days": 1825,
    "response_drafts_days": 730,
    "minimum_hold_days": 365,
}


@dataclass(frozen=True)
class Policy:
    enabled: bool = False
    source_documents_days: int = 1095
    extracted_text_days: int = 1825
    response_drafts_days: int = 730
    minimum_hold_days: int = 365

    @classmethod
    def from_dict(cls, raw: dict | None) -> Policy:
        data = {**DEFAULT_POLICY, **(raw or {})}
        return cls(
            enabled=bool(data.get("enabled")),
            source_documents_days=int(data.get("source_documents_days") or 0),
            extracted_text_days=int(data.get("extracted_text_days") or 0),
            response_drafts_days=int(data.get("response_drafts_days") or 0),
            minimum_hold_days=int(data.get("minimum_hold_days") or 0),
        )

    def as_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "source_documents_days": self.source_documents_days,
            "extracted_text_days": self.extracted_text_days,
            "response_drafts_days": self.response_drafts_days,
            "minimum_hold_days": self.minimum_hold_days,
        }

    def days_for(self, klass: str) -> int:
        return {
            "source_documents": self.source_documents_days,
            "extracted_text": self.extracted_text_days,
            "response_drafts": self.response_drafts_days,
        }.get(klass, 0)

    def effective_days(self, klass: str) -> int:
        """The age at which this class is actually disposed of.

        The floor wins. A policy that says 30 days and a floor that says 365
        disposes at 365 — the more conservative of the two, always, so that
        editing one number in a hurry cannot reach back into last month.
        """
        return max(self.days_for(klass), self.minimum_hold_days)


def validate(policy: Policy) -> list[str]:
    """What is wrong with this policy, in words an admin can act on.

    Returned rather than raised: a settings form wants every problem at once,
    and the caller decides whether a problem is fatal.
    """
    problems: list[str] = []
    if policy.minimum_hold_days < FLOOR_MINIMUM_DAYS:
        problems.append(
            f"The minimum hold is {policy.minimum_hold_days} days. Nothing should be disposed of "
            f"inside {FLOOR_MINIMUM_DAYS} days — that is still inside the window where somebody "
            "can protest an award and ask what you had."
        )
    for klass in CLASSES:
        days = policy.days_for(klass)
        if days <= 0:
            problems.append(
                f"{CLASS_LABELS[klass]} has no retention period set, so nothing in that class "
                "would ever be disposed of. Set a number or turn the policy off."
            )
    if policy.days_for("extracted_text") < policy.days_for("source_documents"):
        problems.append(
            "Extracted text would be disposed of before the files it came from. That leaves "
            "documents nothing can read, which is the worst of both — hold the text at least "
            "as long as the files."
        )
    return problems


@dataclass
class Candidate:
    """One thing a policy would dispose of, and the reason."""

    analysis_id: str
    analysis_title: str
    klass: str
    age_days: int
    due_days: int
    last_activity: str
    detail: str

    def as_dict(self) -> dict:
        return {
            "analysisId": self.analysis_id,
            "analysisTitle": self.analysis_title,
            "class": self.klass,
            "label": CLASS_LABELS.get(self.klass, self.klass),
            "ageDays": self.age_days,
            "dueDays": self.due_days,
            "lastActivity": self.last_activity,
            "detail": self.detail,
        }


@dataclass
class Skipped:
    analysis_id: str
    analysis_title: str
    reason: str

    def as_dict(self) -> dict:
        return {
            "analysisId": self.analysis_id,
            "analysisTitle": self.analysis_title,
            "reason": self.reason,
        }


def eligible(analysis, *, now: datetime) -> str | None:
    """Why this pursuit is not eligible for disposal, or ``None`` if it is.

    A reason string rather than a boolean, because "we kept it" needs an answer
    and "the predicate returned false" is not one.
    """
    if getattr(analysis, "legal_hold", False):
        return "Under legal hold."
    stage = getattr(analysis, "stage", "")
    decision = getattr(analysis, "go_no_go", "undecided")
    if stage not in SETTLED_STAGES and decision != "no-bid":
        return "Still live — a pursuit that has not been decided is never disposed of."
    if last_activity(analysis) is None:
        return "No activity date recorded, so its age cannot be established."
    return None


def last_activity(analysis) -> datetime | None:
    """The most recent thing that happened, not the day it opened.

    A pursuit somebody amended last week is not four hundred days old because
    it was created then, and a clock started at creation would dispose of work
    that is still warm.
    """
    stamps = [
        getattr(analysis, "updated_at", None),
        getattr(analysis, "created_at", None),
    ]
    live = [s for s in stamps if isinstance(s, datetime)]
    if not live:
        return None
    latest = max(live)
    return latest if latest.tzinfo else latest.replace(tzinfo=UTC)


def preview(analyses: list, policy: Policy, *, now: datetime | None = None) -> dict:
    """What this policy would dispose of today, and what it would keep.

    Both halves matter. A preview that lists only the disposals answers "what
    goes"; an admin signing off a retention policy is also asking "what stays,
    and why", and the second list is the one that makes the first one safe to
    approve.
    """
    now = now or datetime.now(UTC)
    due: list[Candidate] = []
    skipped: list[Skipped] = []

    for analysis in analyses:
        title = getattr(analysis, "title", "") or ""
        reason = eligible(analysis, now=now)
        if reason:
            skipped.append(Skipped(getattr(analysis, "id", ""), title, reason))
            continue

        activity = last_activity(analysis)
        age = (now - activity).days
        for klass in CLASSES:
            threshold = policy.effective_days(klass)
            if not threshold or age < threshold:
                continue
            floored = threshold > policy.days_for(klass)
            due.append(
                Candidate(
                    analysis_id=getattr(analysis, "id", ""),
                    analysis_title=title,
                    klass=klass,
                    age_days=age,
                    due_days=threshold,
                    last_activity=activity.isoformat(),
                    detail=(
                        f"Settled {age} days ago; {CLASS_LABELS[klass].lower()} are held for "
                        f"{threshold} days"
                        + (" (raised to the minimum hold)." if floored else ".")
                    ),
                )
            )

    counts: dict[str, int] = {}
    for candidate in due:
        counts[candidate.klass] = counts.get(candidate.klass, 0) + 1

    logger.info("retention_preview", due=len(due), skipped=len(skipped), **counts)
    return {
        "enabled": policy.enabled,
        "policy": policy.as_dict(),
        "due": [c.as_dict() for c in due],
        "skipped": [s.as_dict() for s in skipped],
        "counts": counts,
        "neverDisposed": list(NEVER_DISPOSED),
        "problems": validate(policy),
    }


def horizon(policy: Policy, klass: str, *, now: datetime | None = None) -> datetime:
    """The date before which a pursuit's last activity puts it in scope."""
    now = now or datetime.now(UTC)
    return now - timedelta(days=policy.effective_days(klass))
