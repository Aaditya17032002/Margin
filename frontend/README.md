# Margin — frontend

Next.js (App Router) + TypeScript. Warm editorial / civic design. Every
collection is served by the FastAPI backend; Zustand holds a local copy so the
interface answers immediately, writes are optimistic and sent straight through,
and each action carries a Sonner acknowledgement.

## Run

The frontend needs the backend, Postgres, and Redis. The quickest way to get all
four is from the repository root:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

To run the frontend on its own against a backend already listening on
`localhost:8000`:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The browser talks to the
same origin it loaded from — `next.config.ts` rewrites `/api/v1/*` to
`BACKEND_ORIGIN` (default `http://localhost:8000`), and in the compose topology
Caddy answers those paths before Next sees them. There is no CORS surface and no
API host to configure in the client.

```bash
npm run build    # production build
npm run check    # typecheck + lint
```

| Variable | Default | What it does |
| --- | --- | --- |
| `BACKEND_ORIGIN` | `http://localhost:8000` | Where `npm run dev` proxies `/api/v1/*` |
| `NEXT_PUBLIC_API_URL` | _(unset)_ | Absolute API origin, for a backend on another host |

## Sign in

Accounts are real. Create one at `/signup`; the first visit runs a short
onboarding wizard, then the dashboard. **A new workspace starts empty** — no
analyses, no notifications, no institutional memory. It fills as Margin reads.

Microsoft SSO is stubbed: in `PROVIDER_MODE=mock` it signs you into a demo
account rather than talking to Entra.

## What to look at

The soul of the product is the **Margin rail**: hover any citation chip and the
source clause slides in on the right, highlighted. Then:

1. `/` — landing, with a live demo of the rail
2. `/app/analyses/new` — upload a solicitation; this is what makes everything else appear
3. `/app/analyses/<id>/run` — the reading room, driven by the backend's live event stream
4. `/app/analyses/<id>` — the workspace. Tabs: Go/No-Go, matrix, Q&A, SILENT ledger, amendments
5. `/app` — dashboard (go/no-go gauge, deadlines, review queue)
6. `/style` — the design system, in the same ink as the product

`⌘K` / `Ctrl-K` is the command palette. `?` opens keyboard shortcuts. `→` focuses
the Margin; `Esc` releases it.

## Layout

| Path | What it is |
| --- | --- |
| `src/app` | Routes. Marketing, auth, and `/app/*` under the workspace shell |
| `src/components/domain` | Gauge, findings, wax seal, source viewer, reading room |
| `src/components/shell` | Sidebar, topbar, command palette, Margin rail |
| `src/components/workspace` | Analysis workspace tabs |
| `src/lib/api.ts` | The only place the frontend talks to the backend |
| `src/stores` | Zustand. A local copy of server state, plus optimistic writes |
| `src/hooks/use-workspace-data.ts` | Loads collections after sign-in; keeps the notification stream open |
| `src/data/agents.ts` | Static agent and mode descriptors — the only data that ships with the app |
| `src/types` | The contract the API honours, field for field |

Appearance: **Paper** (default), **Dusk** (warm low-light), **Contrast**. Set in
Settings → Appearance.

Only two things are kept in `localStorage`: the session, so a reload does not
bounce you to the login screen, and preferences, because appearance has to be
right on the first paint. Everything else lives on the server, so it survives a
refresh, a different browser, and a colleague signing in. Destructive actions
offer Undo.
