# Margin — frontend

Next.js (App Router) + TypeScript. Warm editorial / civic design. Front-end only:
Zustand stores persist to `localStorage`, seed data lives in `src/data`, and every
action is optimistic with a Sonner acknowledgement.

## Run

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

```bash
npm run build    # production build
npm run check    # typecheck + lint
```

## Sign in

Any well-formed email and a password of six or more characters works. The form
is pre-filled with:

- **Email:** `a.osei@thornfield.co`
- **Password:** `margin2026`

Microsoft and Google SSO are simulated. First visit runs a short onboarding
wizard, then the dashboard.

## What to look at

The soul of the product is the **Margin rail**: hover any citation chip and the
source clause slides in on the right, highlighted. Then:

1. `/` — landing, with a live demo of the rail
2. `/app` — dashboard (go/no-go gauge, deadlines, review queue)
3. `/app/analyses/new` — start a read, then `/run` for the agent choreography
4. `/app/analyses/an_tea_dlp` — the workspace. Tabs: Go/No-Go, matrix, Q&A, SILENT ledger, amendments
5. `/style` — the design system, in the same ink as the product

`⌘K` / `Ctrl-K` is the command palette. `?` opens keyboard shortcuts. `→` focuses
the Margin; `Esc` releases it.

## Layout

| Path | What it is |
| --- | --- |
| `src/app` | Routes. Marketing, auth, and `/app/*` under the workspace shell |
| `src/components/domain` | Gauge, findings, wax seal, source viewer, reading room |
| `src/components/shell` | Sidebar, topbar, command palette, Margin rail |
| `src/components/workspace` | Analysis workspace tabs |
| `src/stores` | Zustand + persist. The only place durable state is written |
| `src/data` | Seed solicitations (education, health, IT, BAA, public works) |
| `src/types` | The contract a future API would have to honour |

Appearance: **Paper** (default), **Dusk** (warm low-light), **Contrast**. Set in
Settings → Appearance.

CRUD survives a refresh. Destructive actions offer Undo.
