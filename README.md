# Margin — Government Solicitation Capture Intelligence

Margin is a capture-intelligence product that reads government solicitations (RFP, RFI, RFQ, IFB, Sources Sought, BAA, Task Orders) and returns grounded, citation-backed analysis.

Every finding is either answered with a citation to the exact source clause, explicitly marked `SILENT`, or flagged `NEEDS_HUMAN`. A dedicated verifier agent pass re-reads every citation to prevent hallucinations.

---

## Architecture Overview

```
Internet ──▶ Caddy :80/:443 ──┬──▶ frontend:3000   (Next.js App Router)
       (only exposed ports)   ├──▶ backend:8000    (/api/v1/* + SSE)
                              └──▶ internal only:
                                   backend & worker ──▶ db:5432 (pgvector)
                                                    ──▶ redis:6379
```

- **Reverse Proxy**: Caddy terminating TLS, enforcing CSP/HSTS/security headers, and proxying `/api/*` to backend and `/*` to frontend with SSE-friendly streaming.
- **Frontend**: Next.js 15 App Router with Zustand stores.
- **Backend**: FastAPI (Python 3.12+ async), SQLAlchemy 2.0 async, Alembic, Pydantic v2.
- **Agentic Layer**: Schema-first Analysis Spec (Sections A–M), specialist agents (Intake, Scope, Compliance, Eligibility, Evaluation, Risk, Pricing, Q&A), and Citation Verifier.
- **Task Queue**: Arq + Redis for long-running analysis and DOCX report generation.
- **Data & Vector Store**: PostgreSQL 16 + pgvector for per-analysis isolated semantic search.

---

## Quick Start (Production Topology)

The root multi-stage `Dockerfile` builds all targets (`frontend`, `backend`, `worker`). Only ports `80` and `443` are exposed to the host:

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Start the complete stack
docker compose up --build
```

Access the app at:
- **Web UI**: [http://localhost](http://localhost) (or https://localhost)
- **API Documentation**: [http://localhost/api/v1/docs](http://localhost/api/v1/docs)
- **OpenAPI Specification**: [http://localhost/api/v1/openapi.json](http://localhost/api/v1/openapi.json)

---

## Local Development Mode

To run with source code bind-mounts, hot reloading (`uvicorn --reload`, `next dev`), and local debug ports exposed (`127.0.0.1:5432`, `127.0.0.1:6379`, `127.0.0.1:8000`):

```bash
# Start dev services
docker compose -f docker-compose.yml -f docker-compose.dev.yml up

# Run database seed in dev profile
docker compose -f docker-compose.yml -f docker-compose.dev.yml --profile seed up seed
```

---

## Running Offline (Mock Provider)

By default, `PROVIDER_MODE=mock` is enabled in `.env`. This allows the full agentic choreography, in-document extraction, verifier pass, and report generation to run locally and in CI without Azure keys or external network dependencies.

To swap to Azure AI Foundry in production:
```ini
PROVIDER_MODE=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-key
AZURE_DOCINTEL_ENDPOINT=https://your-docintel.cognitiveservices.azure.com/
AZURE_DOCINTEL_KEY=your-key
```

---

## Testing & Quality Assurance

```bash
# Run backend test suite
cd backend
uv run pytest -v

# Run contract tests (asserts backend responses match frontend TypeScript types)
uv run pytest tests/test_contract.py -v

# Run compliance boundary tests (asserts raw doc text never reaches web/Bing layer)
uv run pytest tests/test_boundary.py -v

# Run citation verifier tests
uv run pytest tests/test_verifier.py -v
```

---

## Security & Compliance
- **Database & Cache Isolation**: Postgres and Redis are strictly bound to Docker internal network with no host port exposure in production.
- **Non-Root Containers**: All container processes run as unprivileged non-root users (`node`, `app`) with dropped Linux capabilities (`cap_drop: [ALL]`).
- **Data Boundary Guard**: Web research queries are physically restricted to generic, derived strings — raw document text can never exit the compliance boundary.
- **Argon2id & RBAC**: Passwords hashed with argon2id; granular roles (`admin`, `reviewer`, `writer`, `viewer`) with reviewer-required sign-off on disqualifying findings.
