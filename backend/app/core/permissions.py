"""Who can do what, stated once.

Four roles already existed and meant nothing: every endpoint accepted every
authenticated user, and `role` was a label on a roster page. That is fine while
a workspace is one team and becomes a real problem the moment a subcontractor,
a pricing lead who should not see the technical volume, or a reviewer who
should not be able to close their own round is in the same org.

Permissions are named after the decision they govern rather than after the
table they touch. `sign_off_review` and `resolve_contradiction` are different
authorities even though both write a row, and a matrix built from CRUD verbs
would have collapsed them into "write".

The design rules, in the order they matter:

**Refusals say what is missing and who has it.** A 403 that reads "forbidden"
teaches somebody to file a ticket; one that reads "signing off a review needs
the reviewer role, and Dana has it" gets the work done.

**A reviewer cannot close their own round.** Not a role question — a separation
question, and the one control every organisation running colour teams already
has informally. It is enforced separately from the role matrix because it
depends on who opened the round, not on who is asking.

**Admins are not exempt from separation.** An admin can grant themselves the
role; letting them skip the second pair of eyes would make the control
decorative.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

ADMIN = "admin"
REVIEWER = "reviewer"
WRITER = "writer"
VIEWER = "viewer"

ROLES = (ADMIN, REVIEWER, WRITER, VIEWER)

#: What each role is for, shown when a refusal has to explain itself.
ROLE_PURPOSE = {
    ADMIN: "manages the workspace, its people and its retention settings",
    REVIEWER: "signs off reviews and clears mandatory requirements",
    WRITER: "drafts responses and works the compliance matrix",
    VIEWER: "reads everything and changes nothing",
}


@dataclass(frozen=True)
class Permission:
    name: str
    roles: frozenset[str]
    #: What this authority actually is, in the words of the refusal.
    describes: str


def _p(name: str, describes: str, *roles: str) -> Permission:
    return Permission(name=name, roles=frozenset(roles), describes=describes)


#: Named after the decision, not the table. `sign_off_review` and
#: `resolve_contradiction` are different authorities even though both write a
#: row, and a matrix built from CRUD verbs would collapse them into "write".
PERMISSIONS: dict[str, Permission] = {
    p.name: p
    for p in (
        # ── Reading ──────────────────────────────────────────────────────
        _p("read", "reading an analysis", ADMIN, REVIEWER, WRITER, VIEWER),
        _p("export", "exporting a matrix or a report", ADMIN, REVIEWER, WRITER),
        # ── Ordinary work ────────────────────────────────────────────────
        _p("run_analysis", "running an analysis", ADMIN, REVIEWER, WRITER),
        _p("edit_matrix", "assigning and working the compliance matrix", ADMIN, REVIEWER, WRITER),
        _p("bind_response", "binding a draft response", ADMIN, REVIEWER, WRITER),
        _p("ask_question", "drafting and sending questions to the agency", ADMIN, REVIEWER, WRITER),
        # ── Judgement ────────────────────────────────────────────────────
        _p(
            "clear_requirement",
            "clearing a mandatory requirement",
            ADMIN,
            REVIEWER,
        ),
        _p("resolve_contradiction", "deciding which of two conflicting clauses governs", ADMIN, REVIEWER),
        _p("sign_off_review", "signing off a review round", ADMIN, REVIEWER),
        _p("record_decision", "recording the bid/no-bid decision", ADMIN, REVIEWER),
        # ── The workspace itself ─────────────────────────────────────────
        _p("manage_team", "changing who is in the workspace and what they can do", ADMIN),
        _p("manage_retention", "changing how long documents are kept", ADMIN),
        _p("delete_analysis", "deleting an analysis", ADMIN),
    )
}


def allowed(role: str, permission: str) -> bool:
    entry = PERMISSIONS.get(permission)
    # An unknown permission is refused rather than allowed. A typo in a
    # decorator should close a door, not open one.
    return bool(entry and role in entry.roles)


def require(role: str, permission: str) -> None:
    """Raise a refusal that tells somebody how to get unblocked."""
    if allowed(role, permission):
        return
    entry = PERMISSIONS.get(permission)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unknown permission {permission!r}. Refused because nothing grants it.",
        )
    who = ", ".join(sorted(entry.roles))
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            f"{entry.describes.capitalize()} needs one of these roles: {who}. "
            f"You are a {role}, which {ROLE_PURPOSE.get(role, 'has a narrower remit')}. "
            "A workspace admin can change that."
        ),
    )


def require_separation(*, actor_id: str, opened_by: str, action: str) -> None:
    """The second pair of eyes.

    Not a role question. Every organisation running colour teams already has
    this control informally, and it depends on who opened the round rather than
    on who is asking — so it is enforced apart from the matrix, and admins are
    not exempt. An admin can grant themselves any role; letting them skip this
    would make it decorative.
    """
    if actor_id and opened_by and actor_id == opened_by:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"{action} needs somebody other than the person who opened it. A round signed "
                "off by its own author is a round with one pair of eyes on it, which is the one "
                "thing a colour team exists to prevent."
            ),
        )


def matrix() -> dict:
    """The whole thing, for a settings page to render.

    Shipped as data rather than documented in a wiki, because a permission
    model people cannot see is one they work around.
    """
    return {
        "roles": [
            {"name": role, "purpose": ROLE_PURPOSE[role],
             "permissions": sorted(p.name for p in PERMISSIONS.values() if role in p.roles)}
            for role in ROLES
        ],
        "permissions": [
            {"name": p.name, "describes": p.describes, "roles": sorted(p.roles)}
            for p in PERMISSIONS.values()
        ],
        "separationOfDuties": [
            {
                "action": "Signing off a review round",
                "rule": "Cannot be done by the person who opened it.",
                "why": (
                    "A round signed off by its own author is a round with one pair of eyes on "
                    "it, which is the one thing a colour team exists to prevent."
                ),
            }
        ],
    }
