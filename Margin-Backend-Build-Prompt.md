# Build Prompt — "Margin" Backend + Infrastructure

> Paste everything below the divider into your agentic IDE as the build brief. It
> produces the **backend** for the Margin frontend plus the **full deployable
> project**: one root multi-stage Dockerfile, two compose files (prod + dev), a
> reverse proxy that is the only thing exposed to the host, an internal-only
> database, and a real **schema-driven agentic workflow**. The backend must be
> contract-compatible with the existing Margin frontend (§2).

---

## 0. Role & mission

You are a senior backend + platform engineer. Build the **best possible** backend for
**Margin**, a capture-intelligence product that reads government solicitations
(RFP/RFI/RFQ/IFB/sources-sought/BAA/task order) and returns a **grounded,
citation-backed analysis**. Two things define quality here:

1. **Trustworthy analysis.** Every finding is either answered *with a citation to the
   exact source clause*, explicitly marked `SILENT`, or flagged `NEEDS_HUMAN`. The
   fixed **Analysis Spec schema (§8)** is the core IP — never let the model
   free-form. A **critic/verifier pass** re-checks every citation.
2. **Production-grade platform.** Async, observable, secure by default, one-command
   deploy, DB and internal services never exposed to the host, reverse proxy
   terminates TLS.

Do not cut corners with in-memory hacks. Real Postgres, real migrations, real task
queue, real streaming, real auth.

---

## 1. Context: the frontend already exists

The Margin frontend is a Next.js app with static/mock data and Zustand stores. Your job
is to replace the mock data with a real API **without changing the frontend's data
shapes**. Analyze the frontend's stores and routes (§2), then implement matching
endpoints, streaming, and schemas. Where the frontend currently seeds mock objects, the
backend returns the same object shape.

---

## 2. Frontend analysis → API contract

The frontend's Zustand stores map 1:1 to REST resources. Implement all of them under
`/api/v1`. Shapes must match what the frontend already renders.

| Frontend store / view | Resource | Key endpoints |
|---|---|---|
| `useSessionStore` | Auth | `POST /auth/signup`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/microsoft` (OAuth) |
| `useAnalysesStore` + workspace | Analyses | `GET/POST /analyses`, `GET/PATCH/DELETE /analyses/{id}`, `POST /analyses/{id}/run`, `POST /analyses/{id}/decide`, `POST /analyses/{id}/duplicate`, `GET /analyses/{id}/events` (SSE) |
| Compliance Matrix tab | Matrix | `GET /analyses/{id}/matrix`, `POST/PATCH/DELETE /analyses/{id}/matrix/{rowId}`, `POST /analyses/{id}/matrix/bulk` |
| Q&A Builder tab | Questions | `GET/POST /analyses/{id}/questions`, `PATCH/DELETE …/{qId}`, `PATCH …/reorder` |
| SILENT ledger / findings | Findings | `GET /analyses/{id}/findings`, `PATCH /analyses/{id}/findings/{fieldPath}` (review/override) |
| Amendments/Diff tab | Versions | `GET /analyses/{id}/versions`, `GET /analyses/{id}/diff?from=&to=` |
| `useNotificationsStore` | Notifications | `GET /notifications`, `PATCH /notifications/{id}`, `POST /notifications/read-all`, `GET /notifications/stream` (SSE/WS) |
| `useTeamStore` | Team | `GET/POST /team/members`, `PATCH/DELETE …/{id}`, `POST /team/invites` |
| `useIntegrationsStore` | Integrations | `GET /integrations`, `POST /integrations/{provider}/connect`, `DELETE …/disconnect`, `GET /integrations/{provider}/files`, `POST /integrations/{provider}/import` |
| `useTemplatesStore` | Templates | `GET/POST/PATCH/DELETE /templates` |
| `useKnowledgeStore` | Knowledge base | `GET/POST/PATCH/DELETE /knowledge` (+ vector search) |
| `usePrefsStore` | Preferences | `GET/PUT /preferences` |
| Reports / export center | Reports | `POST /analyses/{id}/report` (generate DOCX), `GET /reports/{id}` (download), `GET /reports` |
| Deadlines view | Deadlines | `GET /deadlines` (derived from analyses) |
| Activity log | Activity | `GET /activity` (audit trail) |
| Global search / ⌘K | Search | `GET /search?q=` (hybrid across analyses + knowledge) |

**Shared contract types** (generate OpenAPI → the frontend can codegen a typed client):
publish `openapi.json`; the `Analysis`, `Finding`, `Citation`, `MatrixRow`,
`Question`, `GoNoGo` types are the source of truth and must match §8.

**Streaming contract:** `POST /analyses/{id}/run` enqueues a job and returns
immediately; the frontend's **agent-choreography view** subscribes to
`GET /analyses/{id}/events` (SSE) and receives ordered events: `agent_started`,
`reasoning_tick`, `finding_emitted`, `agent_completed`, `verification`, `run_completed`.
Emit these so the frontend's roster lights up and findings stream in.

---

## 3. Tech stack (latest, opinionated)

- **Language/runtime:** Python 3.12+, **fully async**.
- **Package/deps:** **uv** (Astral) for install + lockfile + venv. Fast, reproducible.
- **Web framework:** **FastAPI** + Uvicorn (Gunicorn/Uvicorn workers in prod).
- **Data:** **PostgreSQL 16 + pgvector**, **SQLAlchemy 2.0** (async) + **Alembic**
  migrations. Pydantic v2 everywhere.
- **Cache / queue broker:** **Redis 7**.
- **Task orchestration:** **Arq** (async-native) or Celery for long-running analysis
  jobs; jobs stream progress to Redis pub/sub → SSE.
- **Vector/RAG (in-document, self-contained):** **pgvector** for the per-analysis
  scoped index (keeps the DB inside the stack). Azure AI Search is the optional
  scale-up path — behind the same retrieval interface.
- **Agentic layer:** **Azure AI Foundry Agent Service** for multi-agent orchestration,
  with **Deep Research (o3-deep-research) + Grounding with Bing** for external
  research, and **Azure AI Document Intelligence (Layout)** for parsing. Wrap all of
  this behind a **provider interface** (§8.6) so a local/mock provider can run the
  full workflow offline for dev and CI.
- **DOCX generation:** **docxtpl** (Jinja-in-Word templates) + **python-docx** for the
  dynamic compliance-matrix table and citation footnotes.
- **Auth:** JWT (access + refresh) with **argon2** hashing; **MSAL** for Microsoft
  OAuth (ties to the integrations story).
- **Validation/config:** pydantic-settings, 12-factor env.
- **Observability:** structlog (JSON logs), OpenTelemetry traces, Foundry tracing,
  Prometheus metrics, Sentry (optional).
- **Reverse proxy:** **Caddy** (automatic TLS, tiny config) — Traefik acceptable if you
  prefer label-based routing.
- **Testing:** pytest + pytest-asyncio + httpx + testcontainers (Postgres/Redis).

---

## 4. Repository structure & the "one root Dockerfile" pattern

Monorepo. **One** multi-stage Dockerfile at the root with **named build targets**;
both compose files build the services they need from it (this is how a single root
Dockerfile cleanly "runs both frontend and backend" without a two-process container).

```
margin/
├── Dockerfile                 # ROOT multi-stage, targets: frontend, backend, worker
├── docker-compose.yml         # PROD: proxy + frontend + backend + worker + db + redis
├── docker-compose.dev.yml     # DEV override: hot-reload, exposed debug ports, seeds
├── .env.example               # documented; real .env is never committed
├── proxy/
│   └── Caddyfile              # only service bound to host 80/443; security headers, TLS
├── frontend/                  # the existing Next.js app
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app factory, routers, middleware
│   │   ├── api/v1/            # routers per resource (§2)
│   │   ├── core/             # config, security, logging, deps, rate-limit
│   │   ├── db/               # SQLAlchemy models, session, Alembic env
│   │   ├── schemas/          # Pydantic: Analysis Spec (§8) is the moat, DTOs
│   │   ├── agents/           # orchestrator + specialists + verifier (§8)
│   │   ├── pipeline/         # ingest → layout → chunk → embed → index
│   │   ├── providers/        # LLM/agent/docintel/search provider interfaces + Azure + mock
│   │   ├── workers/          # Arq tasks (run_analysis, generate_report, refresh_amendment)
│   │   ├── reports/          # docxtpl templates + renderer
│   │   └── realtime/         # SSE/pubsub, notifications
│   ├── alembic/
│   ├── tests/
│   └── pyproject.toml         # uv-managed
└── README.md
```

**Root Dockerfile (target sketch):**

```dockerfile
# ---- frontend build ----
FROM node:22-slim AS frontend-build
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# ---- frontend runtime ----
FROM node:22-slim AS frontend
WORKDIR /app
ENV NODE_ENV=production
COPY --from=frontend-build /app/.next/standalone ./
COPY --from=frontend-build /app/.next/static ./.next/static
COPY --from=frontend-build /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]

# ---- python base (shared by backend + worker) ----
FROM python:3.12-slim AS py-base
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN pip install uv
WORKDIR /srv
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
COPY backend/ .
RUN addgroup --system app && adduser --system --ingroup app app
USER app

# ---- backend API ----
FROM py-base AS backend
EXPOSE 8000
CMD ["uv","run","gunicorn","app.main:app","-k","uvicorn.workers.UvicornWorker","-b","0.0.0.0:8000","-w","4"]

# ---- background worker ----
FROM py-base AS worker
CMD ["uv","run","arq","app.workers.settings.WorkerSettings"]
```

Compose selects targets via `build: { context: ., dockerfile: Dockerfile, target: backend|frontend|worker }`.

---

## 5. Data model (Postgres + pgvector)

Mirror the frontend entities; async SQLAlchemy 2.0, Alembic migrations, UUID PKs,
`created_at/updated_at`, soft-delete where the UI offers Undo.

Core tables: `orgs`, `users` (argon2 hash, role enum `admin|reviewer|writer|viewer`),
`analyses`, `documents` (base + attachments + amendments, with `version` +
`supersedes`), `doc_chunks` (text, `page`, `section_path`, `bbox`, `embedding
vector(…)` for the scoped in-doc index), `findings` (field_path, value JSONB, `state`
enum `ANSWERED|SILENT|NEEDS_HUMAN`, `confidence`, `stakes` enum
`disqualifying|scored|informational`, `reviewed_by`), `citations` (finding_id, source
`solicitation|web`, doc_id, page, section_path, bbox, quote≤15 words, url), `matrix_rows`,
`questions`, `notifications`, `team_invites`, `integrations` (provider, status, token
ref), `templates`, `knowledge_items` (+ `embedding` for KB search), `reports`,
`activity_log`, `preferences`. Row-level scoping by `org_id` on every query.

---

## 6. API & app-level security

- **JWT** access (short-lived) + refresh (rotating, revocable); argon2id passwords.
- **RBAC** dependency on every route; `disqualifying` findings require reviewer role to
  override.
- **Microsoft OAuth** via MSAL for SSO + integration token acquisition.
- **Rate limiting** (slowapi/Redis) on auth + run + export.
- **Input validation** with Pydantic; strict CORS (only the frontend origin);
  security headers also enforced at the proxy (§12).
- **Secrets** from env/Docker secrets/Key Vault — never in code or image.
- **Audit log** on every state change → feeds `/activity` and the frontend timeline.
- **Multi-tenant isolation**: every query filtered by `org_id`; no cross-org reads.
- **Idempotency keys** on `run` and `report` to prevent duplicate expensive jobs.

---

## 7. Document processing pipeline

`ingest → detect & split (base/attachments/amendments, establish precedence) →
Azure Document Intelligence Layout (headings, tables, page/bbox) → OCR if scanned →
structural chunking (by clause/section, carry {page, section_path, bbox}) →
embed → per-analysis pgvector index (scoped, deleted per retention policy)`.

Amendments **win**: run a conflict pass; when a new amendment is imported, trigger the
`refresh_amendment` worker → re-extract → **diff** vs prior version → notify.

---

## 8. The agentic workflow (core)

### 8.1 Schema-first, always
The **Analysis Spec** is a fixed, **versioned** Pydantic schema encoding the universal
framework (Sections A–M: identity, scope, agency context, compliance, eligibility,
evaluation, submission, technical matrix, risk, market, pricing, post-award, open
questions, go/no-go). Every leaf field is typed and must resolve to
`ANSWERED (+citation +confidence) | SILENT | NEEDS_HUMAN`. Agents fill fields; they do
**not** decide what to look for. Tag each analysis with its `spec_version` for
reproducibility.

### 8.2 Two retrieval systems, kept strictly separate
- **In-document QA** over the scoped pgvector index → citations point to `page/section/
  bbox` of the uploaded doc. Never leaves the stack.
- **External research** → Deep Research (o3-deep-research) + Grounding with Bing on
  **derived, generic queries only** (e.g. "FERPA vendor obligations 2026"), never the
  raw solicitation text. **Compliance rule (enforce in code):** Grounding with Bing
  transfers data outside the Azure compliance boundary, so the pipeline must be
  physically incapable of sending document text to the web layer — only extracted
  generic query strings pass through.

### 8.3 Agent roster (orchestrated on Foundry Agent Service; Connected Agents / A2A)
Orchestrator → specialists (Doc-Intake, Identity & Logistics, Scope-Decoder, Context,
Compliance, Eligibility, Evaluation, Compliance-Matrix, Pricing & Post-Award, Risk &
Red-Flag) → Research agent (Deep Research/Bing on generic queries) → **Critic/Verifier**
→ Q&A-Strategy → Go/No-Go Synthesizer → Report writer. Each specialist owns a slice of
the schema so context stays small and outputs are gradeable.

### 8.4 The verifier is non-negotiable
After extraction, a separate pass re-reads each `ANSWERED` field **against its own
cited span** and asks "does this text actually support this value?" Mismatch →
downgrade to `NEEDS_HUMAN`. This kills hallucinated citations, the fastest way to lose
user trust. Use a reasoning model; keep the prompt narrow.

### 8.5 Confidence & stakes routing
`disqualifying` fields (deadlines, mandatory attendance, eligibility gates) always
require human sign-off regardless of confidence; low-confidence anything → `NEEDS_HUMAN`.

### 8.6 Provider abstraction (so it runs offline)
Define interfaces: `AgentProvider`, `LLMProvider`, `DocIntelProvider`, `SearchProvider`,
`ResearchProvider`. Ship an **Azure** implementation (default) and a **mock/local** one
(canned deterministic findings, local embeddings) so `docker compose up` runs the full
choreography end-to-end without Azure keys — essential for dev, demos, and CI.

### 8.7 Streaming the choreography
The `run_analysis` worker publishes ordered events to Redis pub/sub; the SSE endpoint
relays them to the frontend (`agent_started`, `reasoning_tick`, `finding_emitted`,
`agent_completed`, `verification`, `run_completed`). This drives the frontend's live
"reading room."

### 8.8 Modes
`quick_triage | standard | deep_research | matrix_only | qa_only | amendment_refresh |
recompete_compare` — each selects which agents run and whether the (costly) Deep
Research path is invoked. Gate `deep_research` behind explicit selection.

---

## 9. DOCX report generation

Server-side worker renders the reviewed schema into a branded Word report via docxtpl +
python-docx. Structure: Go/No-Go executive summary → key dates & logistics →
scope decoded → compliance matrix (table) → legal/regulatory (in-doc + web citations) →
eligibility & evaluation → risks → clarifying questions → **appendix: every SILENT
finding**. Every factual line carries its inline citation; mandatory items in `--seal`,
scored in `--ochre`, verified in `--leaf`. Store to volume/blob; expose via
`GET /reports/{id}`; fire a notification + Sonner acknowledgement on completion.

---

## 10. Realtime & notifications

SSE for analysis events and the notifications stream (WebSocket acceptable). Server
emits notifications on: run complete, low-confidence/needs-review findings, deadline
approaching, amendment detected, report ready, integration errors. Persist to
`notifications` + push live → the frontend banner + notifications center.

---

## 11. Observability, config, testing

- structlog JSON logs with request/trace IDs; OpenTelemetry spans across API → worker →
  agent calls; Foundry tracing for agent runs; Prometheus `/metrics`; `/health` +
  `/ready` (checks DB, Redis, provider).
- pydantic-settings config; documented `.env.example`.
- pytest: unit (schema/verifier logic), integration (API via httpx + testcontainers),
  contract tests asserting response shapes match the frontend types, and a
  **golden-set eval** — labeled past solicitations with known answers to measure
  field-level **miss-rate** on every schema change.

---

## 12. Docker, compose, reverse proxy & security (the infra ask)

### Topology
`Caddy (proxy)` is the **only** container bound to host `:80/:443`. Everything else lives
on an **internal** Docker network with **no published ports**. Postgres and Redis are
reachable only from backend/worker. TLS terminates at Caddy (automatic HTTPS in prod;
local CA/self-signed in dev).

```
Internet ─▶ Caddy :443  ─┬─▶ frontend:3000   (Next.js)
   (only exposed port)   ├─▶ backend:8000     /api/*  (+ SSE)
                         └─(internal only)
                     backend & worker ─▶ db:5432 (pgvector)  ·  redis:6379
```

### `docker-compose.yml` (prod) — key hardening
- Two networks: `web` (proxy only) and `internal` (everything). DB/Redis on `internal`
  **only**, **no `ports:`** — never exposed to host.
- `proxy`: `ports: ["80:80","443:443"]`, mounts `./proxy/Caddyfile`, depends_on others'
  healthchecks.
- `frontend`/`backend`/`worker`: `expose` (not `ports`); `build.target` = respective
  stage; env from `.env`/secrets; `restart: unless-stopped`.
- Every service: **non-root user**, `read_only: true` rootfs where feasible +
  `tmpfs` for scratch, `cap_drop: [ALL]`, `security_opt: [no-new-privileges:true]`,
  `healthcheck`, and `deploy.resources.limits` (cpu/mem).
- `db`: named volume `pgdata`, no host port, healthcheck `pg_isready`.
- **Secrets** via Docker secrets (or an untracked `.env`); never baked into images.

### `docker-compose.dev.yml` (override)
- Bind-mount source for **hot reload** (`uvicorn --reload`, `next dev`, `arq --watch`).
- Expose `5432`/`6379`/`8000` **to localhost only** for debugging (`127.0.0.1:5432:5432`).
- Seed script populates realistic demo data matching the frontend's mock fixtures.
- Use the **mock provider** by default so the full workflow runs without Azure keys.
- Run: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`.

### Caddyfile essentials
Reverse-proxy `/api/*` → `backend:8000` (with SSE-friendly settings: no buffering,
long read timeout) and everything else → `frontend:3000`; enforce **HSTS, CSP,
X-Content-Type-Options, Referrer-Policy, X-Frame-Options**, gzip/zstd, and per-route
rate limiting. Automatic HTTPS in prod.

---

## 13. Build order

1. Repo skeleton, uv project, config, structlog, FastAPI app factory, `/health`.
2. Postgres + pgvector + SQLAlchemy models + Alembic + seed script.
3. Auth (JWT + argon2 + RBAC) + Microsoft OAuth stub.
4. CRUD for every resource in §2 with strict org scoping → frontend can drop mock data.
5. Provider interfaces + **mock provider**; get the full agentic run working offline
   with streamed SSE choreography end-to-end.
6. Real pipeline: Document Intelligence layout → chunk → pgvector → in-doc QA.
7. Analysis Spec schema + specialist agents + **verifier** + confidence/stakes routing.
8. External research (Deep Research/Bing) on generic queries, with the boundary guard.
9. Arq workers: `run_analysis`, `generate_report` (DOCX), `refresh_amendment` (+ diff).
10. Notifications + realtime; activity/audit log; search (hybrid).
11. Dockerfile targets, both compose files, Caddy, hardening, healthchecks.
12. Observability, tests, golden-set eval. Ship `docker compose up` → whole product runs.

---

## 14. Definition of done

- `docker compose up` brings up proxy + frontend + backend + worker + db + redis;
  **only 80/443 are reachable from the host**; DB/Redis are not.
- The existing frontend runs against the real API with **no shape changes**; mock stores
  are replaced by live data.
- A full flow works: signup → connect integration (mock) → new analysis → **run** (live
  streamed agent choreography) → review findings with citations → decide → **export
  DOCX** → notification fires.
- Every `ANSWERED` finding carries a verifiable citation; the **verifier** downgrades any
  unsupported one; `SILENT` and `NEEDS_HUMAN` are surfaced, never hidden.
- Raw document text can **never** reach the Bing/web layer (assert this in a test).
- Non-root containers, dropped caps, no secrets in images, migrations run cleanly,
  health/readiness green, OpenAPI published, golden-set miss-rate reported.
- Runs fully offline with the mock provider; swaps to Azure via env only.
