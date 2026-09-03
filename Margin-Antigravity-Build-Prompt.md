# Antigravity Build Prompt — "Margin"

> Paste everything below the line into Antigravity as the project brief. It is
> written as instructions to the agent. It builds a **complete, production-grade,
> front-end-only** application with static data and state-level CRUD — no real
> backend. Every screen, component, and interaction is in scope; there is no
> "phase 2." Rename the product by changing one token (`Margin`) if desired.

---

## 0. Role, mission, and the anti-slop mandate

You are a senior **design engineer**, not a component assembler. You are building
**Margin** — the reference example of what a document-intelligence product can look
like. The bar is *masterpiece*: the kind of interface people screenshot and share.
"Good enough" is a failure. Taste is the differentiator.

**Install and actively apply these three design skills before and during the build:**

1. **impeccable** (`npx impeccable install`, then `/impeccable init`) — run
   `/audit`, `/critique`, `/colorize`, `/typeset`, `/animate`, `/delight`, and
   `npx impeccable detect` against every screen. It must pass with **zero AI-slop
   flags**.
2. **emil-design-eng** — apply the motion craft: every animation must justify itself
   (should this animate? why? which easing? how fast?). Match motion to mood — Margin
   is a *calm, confident, editorial* product, so motion is crisp and elegant, never
   bouncy. Use `ease`/custom cubics, not default `ease-out`. Review animations frame
   by frame; kill anything that jitters.
3. **design-taste-frontend** — do a **critique pass** on every page before calling it
   done. Never ship the first draft. Stronger typography, color, spacing, states,
   accessibility.

**Hard "never do this" list (auto-fail if present):**
- ❌ Inter / Geist-default-everything, system-font-only UIs
- ❌ purple→blue gradients, neon, glassmorphism-for-its-own-sake
- ❌ dark theme as the default, dark neon "hacker" aesthetics
- ❌ cards nested inside cards, gray text on colored backgrounds
- ❌ the rounded-square icon-tile-above-every-heading pattern
- ❌ bounce/overshoot easing on professional controls
- ❌ generic shadcn "as shipped" look — restyle every primitive
- ❌ spinners as the only loading state
- ❌ centered-everything landing pages that look like a template

---

## 1. Product brief

**Margin** is capture-intelligence software for teams that respond to government
solicitations (RFP / RFI / RFQ / IFB / sources-sought / BAA / task orders). You upload
a solicitation; Margin reads every line and produces a **grounded, citation-backed
analysis**: what the agency wants, the rules and compliance regimes that apply,
eligibility gates, evaluation weights, risks, a line-by-line compliance matrix, and a
ready-to-submit list of clarifying questions — each finding traceable to the exact
clause in the source. The team verifies in seconds instead of re-reading 200 pages.

**Users:** capture managers, proposal writers, compliance/legal reviewers, bid
coordinators. High-stakes, detail-obsessed, time-poor. Missing one disqualifying line
loses a bid.

**Emotional target:** *calm mastery.* Opening Margin should feel like sitting at a
beautifully organized desk where the most experienced colleague has already read
everything and laid it out for you — and you can trust it because every claim points
back to the page it came from.

**Signature idea — "the Margin":** a persistent right-hand rail. Touch/focus any
finding anywhere in the app and the cited source clause slides into the Margin with
the document page and the exact line highlighted. Verification is one glance, zero
navigation. This is the soul of the product; make it flawless.

---

## 2. Brand & art direction

**Theme: warm editorial / civic.** Think fine paper, ink, and the patina of bronze
civic architecture — not enterprise SaaS. Light by default. Distinctive, not neon.

### Color tokens (define as CSS variables + Tailwind theme; use OKLCH under the hood)

```css
/* Surfaces — warm paper, never stark white */
--paper:        #F6F2E9;  /* app background */
--paper-raised: #FCFAF4;  /* cards, panels */
--paper-sunk:   #EFEADD;  /* wells, inputs */
--line:         #E4DCCB;  /* hairline borders */
--line-strong:  #D6CBB3;

/* Ink — warm near-black, three levels */
--ink:      #211D17;
--ink-soft: #5B5347;
--ink-faint:#8A8072;

/* Primary — verdigris / patina (aged bronze, civic) */
--patina:      #2F6F63;
--patina-hover:#275C52;
--patina-tint: #E7F0EC;

/* Semantics — a warm civic set, NOT red/green/yellow defaults */
--seal:  #9B2D28;  --seal-tint:  #F3E2DF;  /* disqualifying / hard fail  */
--ochre: #B4791E;  --ochre-tint: #F6ECD6;  /* scored / caution           */
--leaf:  #3F7D53;  --leaf-tint:  #E7F0E3;  /* verified / pass            */
--slate: #3F5C8C;  --slate-tint: #E4E9F2;  /* informational (one blue,   */
                                            /*   used sparingly)          */
--gold-highlight: rgba(235,217,160,0.55);   /* citation highlight overlay */
```

Optional low-light variant **"Dusk"**: a *warm dim parchment* (deep umber surfaces,
cream ink) — NOT a cold neon dark mode. Ship it as an appearance option, not the
default.

### Typography — an editorial trio (never Inter-for-everything)
- **Display / headings:** `Fraunces` (variable serif; use optical sizing + a soft
  axis). Characterful, editorial, confident.
- **UI / body:** `General Sans` (Fontshare) or `Geist Sans` — humanist, clean, but
  distinctive. Never Inter.
- **Citations / data / numbers / doc IDs:** `Geist Mono` (or `JetBrains Mono`).
- Use a proper modular scale, generous line-height for body (~1.6), tight tracking on
  large serif display. Numbers are tabular in tables.

### Motion language
- UI transitions **150–260ms**, custom cubic (e.g. `cubic-bezier(0.32,0.72,0,1)` for
  panels/drawers). Springs only for physical objects (Margin rail slide, kanban drag,
  the go/no-go gauge, wax-seal stamp).
- **Stagger** list entrances (findings settling in ~28ms apart).
- Everything respects `prefers-reduced-motion` (opacity/color only; no transforms).
- Motion clarifies, never decorates. If it doesn't aid comprehension or delight with
  restraint, cut it.

### Iconography
- `lucide-react`, hairline weight, consistent size. No icon-tile-above-heading cliché.
- A small set of **custom motifs**: a wax-seal stamp (disqualifying), a quill/margin
  mark (annotations), a bronze gate (go/no-go).

---

## 3. Tech stack & libraries (exact)

- **Framework:** Next.js (App Router) + **TypeScript**, React Server/Client split but
  **front-end only** — no server actions hitting a DB, no API routes with a backend.
  (Do not mention or scaffold any backend language or service.)
- **Styling:** Tailwind CSS with the token theme above + CSS variables. A few bespoke
  CSS files for signature effects (paper grain, highlight overlay).
- **State:** **Zustand** (+ `immer`) with the **persist** middleware to `localStorage`,
  so all CRUD survives refresh. One store per domain (§4).
- **Components base:** **shadcn/ui** (Radix primitives) — but **restyle every
  component** to the Margin brand; the default look is banned.
- **Motion:** **Framer Motion** (`motion`) + hand-tuned CSS per emil-design-eng.
- **Toasts / acknowledgement banners:** **Sonner** (Emil's) — the global feedback
  system (§9).
- **Drawers / sheets / mobile pickers:** **Vaul** (Emil's).
- **Command palette:** **cmdk** (⌘K / Ctrl-K).
- **Tables / data grid:** **TanStack Table** (compliance matrix, libraries).
- **Drag & drop:** **dnd-kit** (kanban, reorder Q&A).
- **PDF / source viewer:** **react-pdf** (pdf.js) with a custom highlight overlay layer
  for citation bboxes.
- **Forms & validation:** **react-hook-form** + **zod**.
- **Dates:** `date-fns` + a custom timezone-aware deadline component.
- **Charts (restrained):** `visx` or lightweight custom SVG — evaluation-weight donut,
  confidence distribution, deadline timeline. No heavy dashboard chart look.
- **Fonts:** self-host via `next/font` (Fraunces, General Sans/Geist, Geist Mono).

---

## 4. State model & CRUD (static data, real state)

Seed **rich, believable** static data (multiple realistic solicitations across
education, health, IT, public works — with plausible agencies, deadlines, CLINs,
statutes like FERPA/HIPAA/508, M/WBE goals, etc.). All mutations are **optimistic**,
persist to `localStorage`, and fire a Sonner acknowledgement.

Zustand stores (each with full CRUD + selectors):

- `useSessionStore` — mock auth: `user`, `org`, `login()`, `logout()`, `signup()`,
  `isAuthenticated`. Static credential check; any email/password "works" but flows
  behave realistically (loading, success, error states).
- `useAnalysesStore` — the core entity. An **Analysis** has: id, doc metadata, `mode`,
  `stage` (`triage | analyzing | review | decided`), `goNoGo`, and the full schema of
  findings (identity, scope, compliance, eligibility, evaluation, risks, pricing,
  post-award). CRUD + `setStage`, `decide()`, `duplicate()`, `runAnalysis()` (fakes the
  agent choreography, §5).
- `useMatrixStore` — compliance-matrix rows per analysis: requirement text, citation,
  `type` (`shall|should|may`), `stakes`, assigned owner, response location, status.
  Full inline-edit CRUD, bulk actions, filter.
- `useQAStore` — clarifying questions per analysis: text, source finding, `goNoGoImpact`
  flag, order. CRUD + drag-reorder.
- `useNotificationsStore` — in-app notifications: read/unread, type, CRUD, mark-all.
- `useTeamStore` — members, roles (`admin|reviewer|writer|viewer`), invites. CRUD.
- `useIntegrationsStore` — Outlook / SharePoint / OneDrive connection state + a static
  file tree per source for the import picker. connect/disconnect.
- `useTemplatesStore` — report templates + DPA/boilerplate library. CRUD.
- `useKnowledgeStore` — past bids / win-loss / prior awards (institutional memory). CRUD.
- `usePrefsStore` — appearance (Paper/Dusk/High-contrast), default mode, notification
  prefs, keyboard-shortcut toggles, density.

Every create/update/delete/status-change → optimistic state change → Sonner toast with
**Undo** where it makes sense (delete, decide, stage change).

---

## 5. Signature interactions (build these to perfection — they are the product)

1. **The Margin rail.** Right-hand persistent rail. Hovering/focusing any finding,
   matrix row, or citation chip slides the cited source into the rail: the document
   page (react-pdf), the clause highlighted with `--gold-highlight`, plus `page §x.y`
   in mono. Springs in (~240ms, custom cubic). Pin to keep it open. Keyboard: `→`
   focuses the rail, `Esc` releases. This must feel instantaneous and physical.
2. **Agent choreography (analysis-in-progress).** No spinner. When an analysis runs,
   show a live "reading room": the agent roster (Intake, Scope, Compliance,
   Eligibility, Evaluation, Risk, Verifier, Q&A) lights up in sequence; a reasoning
   ticker streams short lines; findings **stream in and settle** into their sections
   with staggered spring entrances; a slim top progress bar fills. Feels like watching
   an expert work, ~6–10s of delightful theater, then resolves to the workspace.
3. **Confidence as ink.** Each finding's text/marker carries subtle ink saturation tied
   to confidence. Low-confidence findings render lighter with a "needs review" quill
   mark and route to a review queue.
4. **Wax-seal for hard gates.** When a disqualifying gate is unmet, an oxblood wax-seal
   stamps down (spring + slight rotation) on the Go/No-Go panel. Satisfying, weighty,
   not cartoonish.
5. **Go/No-Go gauge.** A physical bronze-gate/gauge that animates to position
   (eligibility gates met? timeline realistic? budget/scope sane?). The dashboard hero.
6. **⌘K command palette.** Near-zero-click everything: "New analysis", "Jump to
   deadline", "Export DOCX", "Go to compliance matrix", "Connect SharePoint", switch
   analysis. Fuzzy, grouped, with recent actions.
7. **Optimistic CRUD + acknowledgement.** Every action is instant with a Sonner banner
   (§9); destructive ones offer Undo.
8. **Drag physics.** Reorder Q&A questions and move kanban cards with dnd-kit + spring.
9. **View transitions.** Smooth shared-element transitions between list ↔ workspace
   (View Transitions API / Framer layout).
10. **Empty states that guide** (illustrated, with a single clear next action) — never
    dead ends.

---

## 6. Full route / page map (build all)

**Marketing / entry**
- `/` — landing (editorial hero, product story, the Margin explained with a live demo
  strip, feature grid, "how it reads a document" section, social proof, pricing, CTA,
  footer). Must not look like a template.
- `/pricing`

**Auth & onboarding**
- `/login` — email/password + **Continue with Microsoft** (ties to integrations) +
  Google. Real loading/success/error states.
- `/signup` — multi-field, zod-validated, strength meter.
- `/forgot-password`, `/reset-password`, `/verify-email` (static success).
- `/onboarding` — first-run wizard: org profile → brand/appearance → connect
  Outlook/SharePoint/OneDrive → choose default analysis mode → done. Progress rail,
  skippable, celebratory finish.

**App shell (authenticated, under a layout with sidebar + topbar + ⌘K + Margin rail)**
- `/app` — **Dashboard**: Go/No-Go gauge, upcoming deadlines (countdowns), review
  queue, active analyses, recent activity, KPI tiles.
- `/app/analyses` — all analyses as **kanban** (stages) and a toggle to **table** view;
  filters, search, bulk actions.
- `/app/analyses/new` — **New analysis**: drag-drop upload + import-from-integration
  picker + mode selector (Quick Triage / Standard / Deep Research / Matrix-only /
  Q&A-only / Amendment Refresh / Re-compete Compare) with time/cost hints.
- `/app/analyses/[id]` — **the workspace** (the hero screen; tabbed, §8) with the
  Margin rail. Tabs: Go/No-Go · Overview & Dates · Scope · Compliance Matrix ·
  Legal/Regulatory · Eligibility & Evaluation · Risks & Red Flags · Q&A Builder ·
  SILENT Ledger · Amendments/Diff · Versions & Activity.
- `/app/analyses/[id]/run` — agent-choreography view (§5.2).
- `/app/deadlines` — calendar (month/week) + deadline list with tz-aware countdowns.
- `/app/matrix` — cross-analysis compliance-matrix workspace (standalone).
- `/app/knowledge` — institutional memory / past bids (CRUD).
- `/app/templates` — report templates + DPA/boilerplate library (CRUD, preview).
- `/app/reports` — export center: generate **DOCX**, preview, download history.
- `/app/integrations` — Outlook / SharePoint / OneDrive hub: connect cards, status,
  browse-and-import file tree, export-to-Outlook actions.
- `/app/team` — members, roles, invites (CRUD).
- `/app/notifications` — full notification center (CRUD, filters, mark-all).
- `/app/activity` — audit trail / activity log timeline.
- `/app/search` — global search results.
- `/app/profile` — profile (avatar, details, signature, activity).
- `/app/settings` — tabbed: **Account · Organization · Team & Roles · Integrations ·
  Notifications · Appearance · Analysis Defaults · Billing & Plan · Security · Data &
  Retention · Danger Zone**.
- `/app/help` — help / docs / shortcuts.
- `not-found` (custom 404), global error boundary, per-route loading skeletons.

---

## 7. Component inventory (build all; restyle everything to brand)

**Shell:** collapsible sidebar (with org switcher), topbar (global search, ⌘K trigger,
notifications bell with unread dot, profile menu), breadcrumbs, command palette,
right-hand **Margin rail**, keyboard-shortcuts help dialog, onboarding coachmarks.

**Inputs:** button (primary/secondary/ghost/danger/quiet + icon + split), input,
textarea, select, **combobox**, multi-select, tags input, **timezone-aware datetime
picker**, file **dropzone**, switch, checkbox, radio, slider, **segmented control**,
search field with suggestions.

**Data:** TanStack **table** (sort/filter/paginate/row-select/inline-edit), editable
**data grid** (matrix), **kanban** (dnd-kit), pagination, filter bar.

**Overlay:** dialog, confirm dialog, **Vaul** drawer/sheet, popover, tooltip, hovercard,
dropdown menu, context menu, command palette.

**Feedback:** **Sonner** toasts (success/error/info/warning/action-undo), inline
callouts/banners color-coded by stakes (`--seal`/`--ochre`/`--leaf`/`--slate`),
skeletons + shimmer, progress (linear/circular/step/agent-timeline), empty states,
error states.

**Domain (bespoke):** **citation chip** (→ opens Margin rail), **source card**,
**confidence meter** (ink), **stakes badge** (disqualifying/scored/info), **doc-type
badge**, **wax-seal marker**, **Go/No-Go gauge**, **deadline countdown**, **evaluation-
weight donut**, **agent-roster panel**, **reasoning ticker**, **SILENT ledger item**
(ghosted/dotted treatment), **amendment-diff row** (added/changed/removed), **version
timeline**, **integration connect card**, **file-import tree**.

**Identity:** avatar + group + presence, badges/chips, tabs, accordion, timeline,
calendar, stat/KPI tiles, cards (single-level only — no nesting).

---

## 8. Key screen specs

**Analysis workspace (`/app/analyses/[id]`)** — the masterpiece.
- Left: section nav (the tabs above) with completion + flag counts.
- Center: the active section. Findings render as calm editorial "entries," each with
  its value, a mono citation chip, a confidence ink level, and a stakes badge.
  Mandatory items get `--seal` treatment; scored `--ochre`; verified `--leaf`.
- Right: the **Margin rail** (source viewer + highlight), pinnable.
- Top: title, agency, doc-type badge, stage control, **Go/No-Go** mini-gauge, export.
- **Go/No-Go tab:** the gauge + the four gate answers + "single biggest risk" callout +
  decide (Bid / No-Bid / Watch) with wax-seal animation and Undo.
- **Compliance Matrix tab:** editable data grid — every shall/must/will as a row with
  citation → assign owner + response location + status; filter by type/stakes; export.
- **Q&A Builder tab:** auto-compiled questions (from SILENT + contradictions), drag to
  reorder, toggle "affects go/no-go" (those float to top), one-click "send to Outlook."
- **SILENT Ledger tab:** everything the document didn't say, ghosted, each convertible
  into a Q&A question in one click.
- **Amendments/Diff tab:** pick two versions → highlighted added/changed/removed
  findings; banner if a deadline or gate changed.

**Dashboard, Deadlines, Integrations, Settings, Notifications, Team, Reports** — full,
polished, populated with seed data, each with real empty/loading/error states.

**Auth pages** — editorial split layout (brand story panel + form), never centered-card
boilerplate. Microsoft SSO button is prominent (integration narrative).

---

## 9. Notification & acknowledgement system (Sonner)

Global. Every meaningful action confirms via a Sonner banner, styled to brand (paper
surface, ink text, semantic left-accent):
- **Success:** "Analysis moved to Review." · **with Undo** on destructive/stateful ones.
- **Error:** realistic failure simulations (e.g. "Couldn't reach SharePoint — retry").
- **Info / Warning:** deadline approaching, low-confidence findings need review.
- **Action toasts:** "Report exported" → *Download* / *Open in Outlook*.
Plus the persistent **notifications center** (`/app/notifications`) mirroring these with
read/unread state. Toasts: top-right, subtle stack, Emil-grade easing, auto-dismiss with
hover-pause, swipe to dismiss on touch.

---

## 10. Integrations (static, but real-feeling)

Outlook, SharePoint, OneDrive as first-class connect cards on `/app/integrations` and in
onboarding. Connected state persists in `useIntegrationsStore`. Provide:
- **Import picker:** a Vaul sheet with a static file tree per source; selecting a file
  starts a new analysis.
- **Export actions:** "Email report via Outlook", "Save DOCX to OneDrive", "Send Q&A to
  agency contact" — each fires the right acknowledgement banner.
- Microsoft SSO on login/onboarding ties the narrative together.

---

## 11. Accessibility & performance bars (non-negotiable)

- WCAG 2.2 AA: full keyboard nav, visible focus rings (brand-styled), correct roles/ARIA
  on every interactive component, logical heading order, `prefers-reduced-motion`
  honored everywhere.
- Contrast: verify all ink/semantic tokens on paper surfaces pass AA (impeccable
  `/audit`).
- Perf: self-hosted fonts with `next/font`, lazy-load pdf.js and charts, no layout shift,
  code-split routes, memoize heavy grids/tables.
- Responsive: fluid down to mobile; the Margin rail becomes a Vaul bottom sheet on small
  screens; sidebar collapses to a drawer.

---

## 12. Definition of done (quality gates — run these, fix, repeat)

1. `npx impeccable detect` → **zero** AI-slop flags on every route.
2. `impeccable` `/critique` + `/audit` on every page; apply the fixes.
3. `emil-design-eng` **review-animations** pass; remove any jitter/overshoot; verify
   reduced-motion.
4. `design-taste-frontend` critique pass — confirm it doesn't read as a template.
5. All CRUD works at state level and **persists across refresh**.
6. Every action produces an acknowledgement banner; destructive ones offer Undo.
7. The Margin rail, agent choreography, ⌘K, and Go/No-Go gauge all feel physical and
   instantaneous.
8. Full keyboard-only run-through of a complete flow (login → new analysis → run →
   review → decide → export) with zero mouse.

---

## 13. Build order

1. Design system first: tokens, fonts, Tailwind theme, restyled shadcn primitives,
   motion utilities, Sonner + Vaul + cmdk wired. Prove the look on a style-guide page.
2. App shell + navigation + ⌘K + Margin rail scaffold + all Zustand stores + seed data.
3. Auth + onboarding flows.
4. Dashboard → Analyses (kanban/table) → New Analysis → **Analysis workspace** with all
   tabs and the Margin rail (the bulk of the value).
5. Agent choreography, Go/No-Go, compliance matrix, Q&A builder, SILENT ledger,
   amendment diff.
6. Deadlines, Integrations, Reports/DOCX export, Templates, Knowledge, Team,
   Notifications center, Activity, Search, Settings (all tabs), Profile, Help.
7. Landing + pricing.
8. Quality gates (§12): audit, critique, animation review, a11y, perf. Iterate until it
   is, unmistakably, a masterpiece.

**Deliver a running app (`npm run dev`) with every route reachable, populated, and
polished. No TODOs, no placeholder screens, no "coming soon."**
