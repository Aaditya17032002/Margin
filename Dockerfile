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
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1 \
    PYTHONPATH=/srv \
    PATH="/srv/.venv/bin:$PATH"
RUN pip install uv
WORKDIR /srv
COPY backend/pyproject.toml backend/README.md ./
# Generate lockfile if missing, then install
RUN uv lock 2>/dev/null || true && uv sync --frozen --no-dev 2>/dev/null || uv sync --no-dev
COPY backend/ .
RUN addgroup --system app && adduser --system --ingroup app app
USER app

# ---- backend API ----
FROM py-base AS backend
EXPOSE 8000
# Call venv binaries directly — `uv run` needs a writable cache and breaks under read_only.
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000", "-w", "4"]

# ---- background worker ----
FROM py-base AS worker
CMD ["arq", "app.workers.settings.WorkerSettings"]
