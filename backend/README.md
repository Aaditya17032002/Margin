# Margin — backend

Reserved. Margin is currently a **front-end-only** application: every entity lives in the browser, seeded from
`frontend/src/data` and mutated through Zustand stores that persist to `localStorage`. There is no server, no
database, and no network call in the running product.

This folder exists so the seam is visible. When a real backend arrives, the front end should need to change in
exactly one layer.

## Where the seam is

The stores in `frontend/src/stores` are the only place that reads or writes durable state. Each one exposes a small
set of intent-shaped actions (`createAnalysis`, `setStage`, `acceptFinding`, `updateRow`, …) rather than raw setters,
so a store can be reimplemented against HTTP without touching a single component.

| Store | Domain | Would become |
| --- | --- | --- |
| `session` | Signed-in user, org, onboarding state | `POST /auth/session`, `GET /me` |
| `analyses` | Solicitations, findings, gates, stages | `GET/POST/PATCH /analyses` |
| `matrix` | Compliance requirements | `GET/PATCH /analyses/:id/requirements` |
| `qa` | Questions for the contracting officer | `GET/POST /analyses/:id/questions` |
| `workspace` | Team, integrations, templates, knowledge, notifications, exports, prefs | Assorted resource routes |
| `ui` | Rail source, palette, shortcuts | Stays client-only |

`frontend/src/types/index.ts` is the contract. Those interfaces are what a real API would need to return; they were
written as a wire format first and a view model second.

## The pieces that would actually need a server

1. **Document ingestion.** Parsing PDF/DOCX solicitations into paginated, line-addressable text. Every citation in
   Margin is a `{ docId, page, section, lineStart, lineEnd }` tuple, so the parser must preserve line identity —
   that is the whole product.
2. **The reading pass.** The agent choreography in `frontend/src/components/domain/reading-room.tsx` is a scripted
   simulation over seeded findings. Behind a real backend it becomes a streamed job: agents emit findings as they
   are grounded, and the UI already renders them one at a time as they arrive.
3. **Amendment diffing.** Comparing two versions of a solicitation and re-grounding affected findings.
4. **Integrations.** Microsoft Graph for Outlook, SharePoint, and OneDrive; the file trees in the import picker are
   fixtures shaped like Graph responses.
5. **Export rendering.** Templates currently render in the browser; DOCX and PDF generation belongs server-side.

Nothing above is stubbed here. This is a note, not a skeleton.
