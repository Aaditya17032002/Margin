# Margin — backend

FastAPI (Python 3.12, async), SQLAlchemy 2.0, Alembic, Pydantic v2, Arq on Redis,
PostgreSQL 16 with pgvector. It serves every collection the frontend renders, so
the browser holds no durable state of its own beyond a session token and a
handful of display preferences.

## Run

From the repository root, the dev stack brings up the API, the worker, Postgres
and Redis together:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
docker compose exec backend uv run alembic upgrade head
```

Standalone, against a Postgres and Redis you already have:

```bash
uv sync --extra dev
uv run alembic upgrade head
uv run uvicorn app.main:app --reload          # API on :8000
uv run arq app.workers.settings.WorkerSettings # the worker that does the reading
```

The API refuses to start a run without the worker: `POST /analyses/{id}/run`
enqueues an Arq job and answers 503 if the queue is unreachable, rather than
accepting work nothing will pick up.

```bash
uv run pytest -q       # the suite
uv run ruff check app  # lint
```

Interactive docs live at `/api/v1/docs`, the schema at `/api/v1/openapi.json`.

## What a request touches

| Area | Where |
| --- | --- |
| Routers | `app/api/v1/` — one module per resource |
| Wire shapes | `app/schemas/` — camelCase aliases matching `frontend/src/types` field for field |
| Tables | `app/db/models/` |
| Migrations | `alembic/versions/` |
| Agents | `app/agents/` — specialists, orchestrator, citation verifier |
| Providers | `app/providers/` — Azure or mock, chosen by `PROVIDER_MODE` |
| Background work | `app/workers/` |

`app/schemas` is the contract. Those aliases are what the frontend's TypeScript
interfaces expect, and `tests/test_contract.py` asserts the two stay in step.

## An analysis, from upload to workspace

1. `POST /analyses` creates the record — title, agency, mode, owner. Nothing else.
2. `POST /analyses/{id}/document` stores the file and its extracted text
   (`app/pipeline/extract.py`: pypdf for PDF, python-docx for DOCX, decoded bytes
   otherwise). The text is stored on the row, so a run never depends on the
   container that received the upload still holding the file.
3. `POST /analyses/{id}/run` enqueues `run_analysis_task`.
4. The worker runs the roster for the analysis mode, publishing every agent
   start, reasoning tick and finding to `analysis:{id}:events` on Redis pub/sub.
   `GET /analyses/{id}/events` relays that channel as SSE — it sends a
   `stream_ready` frame once subscribed, and clients wait for it before asking
   for a run, because the channel has no replay.
5. The verifier re-reads every finding against its cited span, downgrading
   anything it cannot ground.
6. `app/workers/derive.py` turns the agents' Finding dialect into the shapes the
   workspace reads — evaluation factors keep their weight, risks their severity,
   eligibility findings become gates with `met: null` for a human to answer —
   and the worker writes matrix rows, questions, a notification and an audit
   entry before publishing `run_completed`.

Eligibility gates deliberately arrive unanswered. Whether a bidder clears one is
a fact about the company, not about the document.

## Provisioning and tenancy

Signing up creates an org and its first user, adds that user to the team roster,
and creates the three integration rows so there is something to connect. Nothing
else is created.

`orgs.domain` is deliberately not unique. A second signup from a company's mail
domain gets its own workspace rather than landing in an existing tenant's:
a mail domain is not proof of belonging, and the alternative hands a stranger
someone else's documents. Colleagues join by invitation.

Every query is scoped by `org_id`. Deletes of an analysis are soft, so
`POST /analyses/{id}/restore` returns the same record with the id its matrix rows
and questions still reference.

## Demo data

There is none by default, and that is the intended state. `app/db/seed.py` exists
as an opt-in populate for demos:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile seed up seed
```
