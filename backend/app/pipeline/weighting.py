"""Where the score is, and whether the response is there.

A compliance matrix treats every requirement as equally worth answering.
Evaluators do not. Section M says technical approach is forty percent and past
performance is ten, and a team with four days left should spend them on the
forty — but nothing in the product knew which requirements sat under which
factor, so effort went to whatever was red.

This maps evaluation factors to the requirements that fall under them, and then
to what the response does about those requirements. The output is one ordering:
**weight × weakness**, so the top of the list is the place where the most
points are least defended.

Two things it deliberately does not do.

It does not predict a score. Nothing here knows how an evaluator reads, and a
number that looked like a score would be believed. It reports coverage under a
factor, which is a fact.

It does not reassign requirements. A requirement maps to a factor because their
words overlap or because the factor's own text names the clause — a
deterministic, checkable association a person can disagree with. A model
deciding which requirements "belong to" past performance would be inventing the
structure it claims to have found.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.pipeline.anchor import normalize

logger = get_logger()

#: Below this the requirement is not about the factor, it merely shares
#: vocabulary with it. Every solicitation says "the Offeror shall" everywhere.
MATCH_FLOOR = 0.12

#: A factor with no weight stated. Reported as unweighted rather than as zero:
#: "Basis for Award" is not worth nothing, it is not a scored factor.
UNWEIGHTED = "unweighted"

#: Words that carry no information about which factor a requirement belongs to.
_NOISE = frozenset(
    """the a an of and or to in on at by for with from into any all such other than that this
    these those shall must will may not be is are was were been being have has had contractor
    offeror government proposal proposals response section volume page shall_not factor
    evaluation evaluated award offerors provide provides submit submitted include included
    describe description approach plan""".split()
)

#: A clause reference inside a factor's own description — "as described in
#: Section L.4.2". When a factor names a clause, that is a far stronger signal
#: than any amount of shared vocabulary.
_REFERENCE = re.compile(
    r"(?ix)\b(?:section|clause|paragraph|attachment|exhibit|volume|tab|factor)?\s*"
    r"([A-Z]{1,2}[.\-]\d+(?:\.\d+)*)\b"
)

#: How bad each verdict is for a factor's score. `unverifiable` sits between a
#: gap and an answer because it is genuinely unknown — treating it as either
#: would be a guess in a number people act on.
_WEAKNESS = {
    "satisfied": 0.0,
    "partial": 0.5,
    "unverifiable": 0.6,
    "failed": 1.0,
    "not_found": 1.0,
}


@dataclass
class FactorCoverage:
    """One evaluation factor, and what the response does about it."""

    factor_id: str
    name: str
    weight: float
    #: Share of the total stated weight. Reported separately from `weight`
    #: because solicitations state weights as percentages, points, or nothing.
    share: float
    method: str
    citation: dict
    requirement_ids: list[str] = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    #: 0 when every requirement under this factor is answered, 1 when none is.
    weakness: float = 0.0
    #: weight share × weakness. The ordering that matters.
    exposure: float = 0.0
    #: Requirements under this factor that are mandatory and unanswered.
    blocking: list[str] = field(default_factory=list)
    matched_by: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "factorId": self.factor_id,
            "name": self.name,
            "weight": self.weight,
            "share": round(self.share, 4),
            "method": self.method,
            "citation": self.citation,
            "requirementIds": self.requirement_ids,
            "requirements": len(self.requirement_ids),
            "counts": self.counts,
            "weakness": round(self.weakness, 4),
            "exposure": round(self.exposure, 4),
            "blocking": self.blocking,
            "matchedBy": self.matched_by,
        }


def _terms(text: str) -> set[str]:
    return {word for word in normalize(text).split() if word not in _NOISE and len(word) > 3}


def _references(text: str) -> set[str]:
    return {match.group(1).upper() for match in _REFERENCE.finditer(text or "")}


def match(factor: dict, requirement) -> tuple[float, str]:
    """How strongly one requirement belongs to one factor, and on what evidence.

    Two signals, in order of how much they are worth. A factor that names a
    clause is telling you directly which requirements it scores. Failing that,
    shared distinctive vocabulary — which is weaker, and is why the floor
    exists.
    """
    reference = (getattr(requirement, "reference", "") or "").upper()
    named = _references(f"{factor.get('name', '')} {factor.get('method', '')}")
    if reference and any(reference.startswith(ref) or ref.startswith(reference) for ref in named):
        return 1.0, "the factor names this clause"

    factor_terms = _terms(f"{factor.get('name', '')} {factor.get('method', '')}")
    requirement_terms = _terms(getattr(requirement, "text", "") or "")
    if not factor_terms or not requirement_terms:
        return 0.0, ""

    overlap = len(factor_terms & requirement_terms) / len(factor_terms)
    if overlap < MATCH_FLOOR:
        return 0.0, ""
    shared = sorted(factor_terms & requirement_terms)[:4]
    return overlap, f"shares {', '.join(shared)}"


def build(
    factors: list[dict], requirements: list, checks: list | None = None
) -> list[FactorCoverage]:
    """Every factor, the requirements under it, and how well they are answered."""
    open_requirements = [r for r in requirements if getattr(r, "state", "open") == "open"]
    by_requirement = {}
    for check in checks or []:
        by_requirement[check.requirement_id] = check

    weights = [float(f.get("weight") or 0) for f in factors]
    total_weight = sum(w for w in weights if w > 0)

    out: list[FactorCoverage] = []
    for factor in factors:
        weight = float(factor.get("weight") or 0)
        coverage = FactorCoverage(
            factor_id=str(factor.get("id") or ""),
            name=str(factor.get("name") or ""),
            weight=weight,
            share=(weight / total_weight) if total_weight and weight > 0 else 0.0,
            method=str(factor.get("method") or ""),
            citation=factor.get("citation") or {},
        )

        scored: list[float] = []
        for requirement in open_requirements:
            strength, why = match(factor, requirement)
            if strength <= 0:
                continue
            coverage.requirement_ids.append(requirement.id)
            coverage.matched_by[requirement.id] = why

            check = by_requirement.get(requirement.id)
            status = check.status if check else "unchecked"
            coverage.counts[status] = coverage.counts.get(status, 0) + 1
            if check is not None:
                scored.append(_WEAKNESS.get(status, 0.6))
                if (
                    getattr(requirement, "stakes", "scored") == "disqualifying"
                    and status in ("failed", "not_found")
                ):
                    coverage.blocking.append(requirement.reference)
            # A requirement with no check contributes to the count and not to
            # the weakness: no response is bound, or it was never checked, and
            # calling that either a gap or an answer would put a number in
            # front of somebody that means nothing.

        coverage.weakness = sum(scored) / len(scored) if scored else 0.0
        coverage.exposure = coverage.share * coverage.weakness
        out.append(coverage)

    # Most exposed first: the place where the most points are least defended.
    out.sort(key=lambda c: (-c.exposure, -c.share, c.name))
    logger.info(
        "weighting_built",
        factors=len(out),
        weighted=sum(1 for c in out if c.weight > 0),
        total_weight=total_weight,
    )
    return out


def summarise(coverage: list[FactorCoverage]) -> dict:
    """The one sentence a capture manager reads.

    `unweighted` is reported rather than hidden: a solicitation that states no
    weights at all is common, and a lens that silently showed every factor as
    equally important would be inventing the thing it exists to reveal.
    """
    weighted = [c for c in coverage if c.weight > 0]
    unweighted = [c for c in coverage if c.weight <= 0]
    unmapped = [c for c in coverage if not c.requirement_ids]

    exposed = [c for c in weighted if c.exposure > 0]
    return {
        "factors": len(coverage),
        "weighted": len(weighted),
        "unweighted": len(unweighted),
        "unmapped": [c.name for c in unmapped],
        "weightAtRisk": round(sum(c.share * c.weakness for c in weighted), 4),
        "mostExposed": [
            {"name": c.name, "share": round(c.share, 4), "weakness": round(c.weakness, 4)}
            for c in exposed[:5]
        ],
        "blocking": sorted({ref for c in coverage for ref in c.blocking}),
    }
