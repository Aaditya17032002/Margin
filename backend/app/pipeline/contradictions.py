"""Requirements in the same package that cannot both be met.

A solicitation is written by several people over several months and amended by
more of them. Section L says forty pages, Attachment L-2 says fifty, and an
amendment says sixty-five. All three are extracted correctly, all three sit in
the ledger looking equally authoritative, and the team writes to whichever one
they happened to read.

Nothing else in Margin catches this. Coverage says everything was read. The
sweep found all three. The compliance matrix lists all three as open
requirements. Each is individually right, and together they are a trap.

Detection is deterministic, and deliberately narrow. Every rule here compares
two requirements that state the *same kind of countable thing* and disagree
about the number — page limits, word limits, font sizes, dates, file sizes,
copies — plus the one non-numeric case that matters: a prohibition contradicted
by a permission. Anything softer would produce a page of "these two clauses
sound related", which is a worse outcome than silence, because a list of
maybe-conflicts trains people to close the tab.

**Precedence is proposed, never applied.** Amendments beat the base document
and attachments beat generic language — both true, both wrong often enough that
a machine deciding on its own would be picking which requirement a team writes
to. So a contradiction is raised with a recommendation and a reason, and a
person resolves it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.logging import get_logger

logger = get_logger()

#: How much a requirement's kind matters when two disagree.
KIND_ORDER = {"base": 0, "attachment": 1, "amendment": 2, "response": 3}


@dataclass
class Claim:
    """A countable assertion a requirement makes."""

    dimension: str
    #: Normalised so 8 and "eight" and "8 pages" compare equal.
    value: str
    #: The exact words the value came from, for the reviewer to read.
    quote: str


@dataclass
class Contradiction:
    """Two requirements in the same package that cannot both be met."""

    key: str
    dimension: str
    left_id: str
    right_id: str
    left_value: str
    right_value: str
    summary: str
    #: Which one probably governs, and why. A recommendation, not a decision.
    recommended_id: str = ""
    rationale: str = ""
    severity: str = "blocking"

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "dimension": self.dimension,
            "leftId": self.left_id,
            "rightId": self.right_id,
            "leftValue": self.left_value,
            "rightValue": self.right_value,
            "summary": self.summary,
            "recommendedId": self.recommended_id,
            "rationale": self.rationale,
            "severity": self.severity,
        }


# ── Extracting the countable claim ───────────────────────────────────────

_NUMBER_WORDS = {
    "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12",
}

#: Each dimension is a thing a solicitation states a single number for, where
#: two different numbers in the same package is a contradiction rather than two
#: requirements. `scope` narrows the comparison: a page limit for Volume I and
#: one for Volume II are not in conflict.
_DIMENSIONS: list[tuple[str, re.Pattern]] = [
    (
        "page_limit",
        re.compile(
            r"""(?ix)
            (?:not\s+(?:to\s+)?exceed|no\s+(?:more\s+than|longer\s+than)|maximum\s+of|limited\s+to)
            \s+(?P<value>[\d,]{1,5}|\w+)\s*(?:total\s+)?pages
            | (?P<value2>[\d,]{1,5})\s*-?\s*page\s+(?:limit|maximum)
            """
        ),
    ),
    (
        "word_limit",
        re.compile(
            r"""(?ix)
            (?:not\s+(?:to\s+)?exceed|no\s+more\s+than|maximum\s+of|limited\s+to)
            \s+(?P<value>[\d,]{1,7})\s*words
            """
        ),
    ),
    ("font_size", re.compile(r"(?ix)\b(?P<value>\d{1,2})\s*-?\s*(?:point|pt)\b")),
    ("margin", re.compile(r"(?ix)\b(?P<value>\d+(?:\.\d+)?)\s*-?\s*inch\s+margins?\b")),
    (
        "file_size",
        re.compile(r"(?ix)\b(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>KB|MB|GB)\b"),
    ),
    (
        "copies",
        re.compile(
            r"(?ix)\b(?P<value>\d+|one|two|three|four|five|six)\s+"
            r"(?:hard\s+cop(?:y|ies)|paper\s+cop(?:y|ies)|bound\s+cop(?:y|ies)|copies)\b"
        ),
    ),
    (
        "deadline",
        re.compile(
            r"""(?ix)
            (?:due|closing|deadline|no\s+later\s+than|not\s+later\s+than|by)\s+
            (?:.{0,20}?)
            (?P<value>
                \d{4}-\d{2}-\d{2}
              | (?:January|February|March|April|May|June|July|August|September|October|November|December)
                \s+\d{1,2},?\s+\d{4}
              | \d{1,2}/\d{1,2}/\d{2,4}
            )
            """
        ),
    ),
]

_VOLUME = re.compile(r"(?i)\bvolume\s+([IVX]+|\d+)\b")
#: The words that make a page limit about one part of a response rather than
#: the whole of it. Without this, "the executive summary shall not exceed 2
#: pages" contradicts "proposals shall not exceed 40 pages".
_SCOPE = re.compile(
    r"""(?ix)\b(
        executive\s+summary | cover\s+letter | transmittal\s+letter | resum(?:e|é)s?
      | past\s+performance | technical\s+(?:volume|approach) | management\s+(?:volume|plan)
      | (?:price|cost)\s+(?:volume|proposal) | oral\s+presentation | appendix | attachment
      | each\s+(?:section|volume|reference) | per\s+(?:section|volume|reference)
      | quality\s+control\s+plan | staffing\s+plan | transition\s+plan
      | tables? | figures? | graphics? | charts? | captions? | footnotes?
      | headers? | footers? | title\s+page | table\s+of\s+contents
    )\b"""
)


def claims_of(text: str) -> list[Claim]:
    """Every countable assertion in one requirement."""
    found: list[Claim] = []
    for dimension, pattern in _DIMENSIONS:
        for match in pattern.finditer(text):
            raw = match.groupdict().get("value") or match.groupdict().get("value2") or ""
            value = _normalise(raw)
            if not value:
                continue
            if dimension == "file_size":
                value = f"{value}{(match.groupdict().get('unit') or '').upper()}"
            found.append(Claim(dimension=dimension, value=value, quote=match.group(0).strip()))
    return found


def scope_of(text: str) -> str:
    """What part of the response a claim is about.

    Two page limits in the same package are only in conflict when they govern
    the same thing. A limit on the executive summary and one on the proposal
    are both true.
    """
    volume = _VOLUME.search(text)
    if volume:
        return f"volume:{_roman(volume.group(1))}"
    part = _SCOPE.search(text)
    if part:
        return f"part:{' '.join(part.group(1).lower().split())}"
    return "whole"


def _normalise(raw: str) -> str:
    value = raw.strip().lower().replace(",", "")
    value = _NUMBER_WORDS.get(value, value)
    if re.fullmatch(r"\d+(?:\.\d+)?", value):
        # 12 and 12.0 are the same limit.
        return str(int(float(value))) if float(value).is_integer() else value
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return value
    parsed = _as_date(value)
    return parsed or ""


def _as_date(value: str) -> str:
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
        "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    }
    named = re.fullmatch(r"([a-z]+)\s+(\d{1,2}),?\s+(\d{4})", value)
    if named and named.group(1) in months:
        return f"{named.group(3)}-{months[named.group(1)]:02d}-{int(named.group(2)):02d}"
    slashed = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{2,4})", value)
    if slashed:
        year = int(slashed.group(3))
        year += 2000 if year < 100 else 0
        return f"{year}-{int(slashed.group(1)):02d}-{int(slashed.group(2)):02d}"
    return ""


# ── The non-numeric case worth catching ──────────────────────────────────

#: A prohibition and a permission over the same subject. Narrow on purpose:
#: the subject has to be a named, specific thing, or every "may" in the
#: document collides with every "shall not".
_PROHIBITION = re.compile(
    r"(?ix)\b(?:may\s+not|shall\s+not|must\s+not|is\s+prohibited\s+from|are\s+prohibited\s+from|"
    r"no\s+\w+\s+shall)\s+(?P<verb>\w+)"
)
#: "may" is a permission; "may not" is the prohibition above. Without the
#: lookahead every prohibition matched as its own permission and contradicted
#: itself.
_PERMISSION = re.compile(
    r"(?ix)\b(?:may|is\s+permitted\s+to|are\s+permitted\s+to|can)\s+(?!not\b)(?P<verb>\w+)"
)

#: Function words only. Dropping nouns like "data" or "personnel" here was a
#: mistake: they are exactly what makes two clauses about the same thing.
_FUNCTION_WORDS = frozenset(
    """the a an of and or to in on at by for with from into any all such other than that this
    these those be is are was were been being have has had will shall may must not""".split()
)

#: How far past the verb to read. The direct object is what decides whether two
#: clauses collide; a whole sentence of tail brings in everything else in the
#: paragraph and turns coincidence into a match.
_OBJECT_WORDS = 8


def _subject(text: str, after: int) -> set[str]:
    """The object of the verb — what is being forbidden or permitted."""
    tail = re.findall(r"[a-z]{3,}", text[after : after + 120].lower())
    words: list[str] = []
    for word in tail:
        if word in _FUNCTION_WORDS:
            continue
        words.append(word)
        if len(words) >= _OBJECT_WORDS:
            break
    return set(words)


# ── Detection ────────────────────────────────────────────────────────────


@dataclass
class Candidate:
    """A requirement as this module needs to see it."""

    id: str
    reference: str
    text: str
    kind: str
    document_kind: str
    stakes: str
    state: str = "open"

    @property
    def precedence(self) -> int:
        return KIND_ORDER.get(self.document_kind, 0)


def detect(requirements: list[Candidate]) -> list[Contradiction]:
    """Every pair that states the same countable thing and disagrees."""
    live = [r for r in requirements if r.state == "open"]
    found: list[Contradiction] = []
    found += _numeric(live)
    found += _prohibitions(live)

    # Stable order: worst first, then by dimension, so a re-run does not
    # reshuffle a list somebody is working through.
    found.sort(key=lambda c: (0 if c.severity == "blocking" else 1, c.dimension, c.key))
    logger.info("contradictions_detected", total=len(found))
    return found


def _numeric(requirements: list[Candidate]) -> list[Contradiction]:
    # (dimension, scope) → [(requirement, claim)]
    buckets: dict[tuple[str, str], list[tuple[Candidate, Claim]]] = {}
    for requirement in requirements:
        scope = scope_of(requirement.text)
        for claim in claims_of(requirement.text):
            buckets.setdefault((claim.dimension, scope), []).append((requirement, claim))

    out: list[Contradiction] = []
    for (dimension, scope), entries in buckets.items():
        values = {claim.value for _, claim in entries}
        if len(values) < 2:
            continue
        # Compare each distinct value against the first that differs from it,
        # rather than every pair: three page limits is one problem to resolve,
        # not three.
        seen: dict[str, tuple[Candidate, Claim]] = {}
        for requirement, claim in entries:
            seen.setdefault(claim.value, (requirement, claim))
        ordered = sorted(seen.items(), key=lambda item: item[1][0].precedence)
        base_value, (base_req, base_claim) = ordered[0]
        for value, (requirement, claim) in ordered[1:]:
            if requirement.id == base_req.id:
                # One sentence stating a rule and its exception — "12-point
                # body text; tables may be 10-point". A requirement cannot
                # contradict itself, and reporting that it does is the fastest
                # way to teach somebody to ignore this tab.
                continue
            out.append(
                _contradiction(dimension, scope, base_req, base_claim, requirement, claim)
            )
    return out


def _contradiction(
    dimension: str,
    scope: str,
    left: Candidate,
    left_claim: Claim,
    right: Candidate,
    right_claim: Claim,
) -> Contradiction:
    where = "" if scope == "whole" else f" for {scope.split(':', 1)[1]}"
    label = dimension.replace("_", " ")

    recommended, rationale = _recommend(left, right)
    return Contradiction(
        key=f"{dimension}:{scope}:{min(left.id, right.id)}:{max(left.id, right.id)}",
        dimension=dimension,
        left_id=left.id,
        right_id=right.id,
        left_value=left_claim.value,
        right_value=right_claim.value,
        summary=(
            f"Two different {label}s{where}: {left.reference} says {left_claim.quote}, "
            f"{right.reference} says {right_claim.quote}."
        ),
        recommended_id=recommended,
        rationale=rationale,
        # A deadline or a page limit stated twice differently can lose the bid
        # on its own. Anything else is scored.
        severity="blocking"
        if dimension in ("page_limit", "deadline", "word_limit")
        or "disqualifying" in (left.stakes, right.stakes)
        else "important",
    )


def _recommend(left: Candidate, right: Candidate) -> tuple[str, str]:
    """Which one probably governs.

    Two rules of solicitation reading, in order. An amendment supersedes what
    it amends — the least controversial rule there is. And a specific
    instruction beats a general one, which is true often enough to be worth
    saying and wrong often enough that a machine must not act on it alone.
    """
    if left.precedence != right.precedence:
        later = left if left.precedence > right.precedence else right
        earlier = right if later is left else left
        return (
            later.id,
            f"{later.reference} is in {_kind_words(later.document_kind)} and "
            f"{earlier.reference} is in {_kind_words(earlier.document_kind)}. "
            "An amendment supersedes what it amends, and an attachment usually states the "
            "detail a base document summarises — but check that this one does.",
        )
    return (
        "",
        "Both are in the same document, so neither obviously supersedes the other. "
        "This needs a person to read both clauses, and probably a question to the agency.",
    )


def _kind_words(kind: str) -> str:
    return {
        "base": "the base solicitation",
        "attachment": "an attachment",
        "amendment": "an amendment",
        "response": "the response",
    }.get(kind, kind)


def _prohibitions(requirements: list[Candidate]) -> list[Contradiction]:
    prohibitions: list[tuple[Candidate, str, set[str]]] = []
    permissions: list[tuple[Candidate, str, set[str]]] = []

    for requirement in requirements:
        for match in _PROHIBITION.finditer(requirement.text):
            prohibitions.append(
                (requirement, match.group("verb").lower(), _subject(requirement.text, match.end()))
            )
        for match in _PERMISSION.finditer(requirement.text):
            permissions.append(
                (requirement, match.group("verb").lower(), _subject(requirement.text, match.end()))
            )

    out: list[Contradiction] = []
    for banned_req, banned_verb, banned_subject in prohibitions:
        for allowed_req, allowed_verb, allowed_subject in permissions:
            if allowed_req.id == banned_req.id or banned_verb != allowed_verb:
                continue
            # The verb already had to match exactly, which does most of the
            # work. Two shared words from the direct object on top of that is
            # a real collision; one is coincidence in a document this
            # repetitive, and a page of maybe-conflicts trains people to close
            # the tab.
            shared = banned_subject & allowed_subject
            if len(shared) < 2:
                continue
            recommended, rationale = _recommend(banned_req, allowed_req)
            out.append(
                Contradiction(
                    key=f"permission:{min(banned_req.id, allowed_req.id)}:{max(banned_req.id, allowed_req.id)}",
                    dimension="permission",
                    left_id=banned_req.id,
                    right_id=allowed_req.id,
                    left_value=f"may not {banned_verb}",
                    right_value=f"may {allowed_verb}",
                    summary=(
                        f"{banned_req.reference} forbids what {allowed_req.reference} permits "
                        f"({banned_verb}, {', '.join(sorted(shared)[:4])})."
                    ),
                    recommended_id=recommended,
                    rationale=rationale,
                    severity="blocking",
                )
            )
    return out


def _roman(value: str) -> str:
    numerals = {"1": "I", "2": "II", "3": "III", "4": "IV", "5": "V", "6": "VI"}
    return numerals.get(value.strip(), value.strip().upper())


# ── Reconciliation ───────────────────────────────────────────────────────


async def reconcile(db, *, analysis_id: str, org_id: str, found: list[Contradiction], run_id: str):
    """Persist what this run found, keeping what a person already decided.

    Same rule the Requirement Ledger follows: a contradiction somebody resolved
    stays resolved, and one that stops being detected is closed with a reason
    rather than deleted. A conflict quietly disappearing is indistinguishable
    from a parser that stopped noticing it.
    """
    import uuid
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.db.models.contradiction import Contradiction as Row

    now = datetime.now(UTC)
    existing = list(
        (await db.execute(select(Row).where(Row.analysis_id == analysis_id))).scalars().all()
    )
    by_key = {row.key: row for row in existing}
    seen = {item.key for item in found}

    added = 0
    for item in found:
        row = by_key.get(item.key)
        if row is None:
            row = Row(
                id=f"cx_{uuid.uuid4().hex[:12]}",
                analysis_id=analysis_id,
                org_id=org_id,
                key=item.key,
                state="open",
                first_seen_at=now,
                history=[{"at": now.isoformat(), "event": "detected", "detail": item.summary}],
            )
            db.add(row)
            by_key[item.key] = row
            added += 1
        # The detected half is refreshed; the decided half is never touched.
        row.dimension = item.dimension
        row.left_id, row.right_id = item.left_id, item.right_id
        row.left_value, row.right_value = item.left_value, item.right_value
        row.summary = item.summary
        row.recommended_id = item.recommended_id
        row.rationale = item.rationale
        row.severity = item.severity
        row.last_seen_run = run_id

    closed = 0
    for row in existing:
        if row.key in seen or row.state != "open":
            continue
        row.state = "dismissed"
        row.history = [
            *(row.history or []),
            {
                "at": now.isoformat(),
                "event": "no_longer_detected",
                "detail": (
                    f"Not found in run {run_id}. Either an amendment resolved it or the "
                    "extraction stopped seeing one of the clauses — the two look identical "
                    "from here."
                ),
            },
        ]
        closed += 1

    await db.flush()
    logger.info(
        "contradictions_reconciled",
        analysis_id=analysis_id,
        found=len(found),
        added=added,
        closed=closed,
    )
    return {"found": len(found), "added": added, "closed": closed}
