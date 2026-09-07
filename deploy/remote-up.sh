#!/usr/bin/env bash
# Pull Margin images and (re)start the stack on the shared Azure host.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

: "${DOCKERHUB_USERNAME:=aditya17032002}"
: "${MARGIN_TAG:=latest}"

export MARGIN_FRONTEND_IMAGE="${MARGIN_FRONTEND_IMAGE:-${DOCKERHUB_USERNAME}/margin-frontend:${MARGIN_TAG}}"
export MARGIN_BACKEND_IMAGE="${MARGIN_BACKEND_IMAGE:-${DOCKERHUB_USERNAME}/margin-backend:${MARGIN_TAG}}"
export MARGIN_WORKER_IMAGE="${MARGIN_WORKER_IMAGE:-${DOCKERHUB_USERNAME}/margin-worker:${MARGIN_TAG}}"

if [[ ! -f .env ]]; then
  echo "missing .env in $ROOT — copy the production env before deploying" >&2
  exit 1
fi

if [[ -n "${DOCKERHUB_READONLY_TOKEN:-}" ]]; then
  echo "$DOCKERHUB_READONLY_TOKEN" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin
fi

docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans

# Apply migrations after the API image is up.
docker compose -f docker-compose.prod.yml exec -T -e PYTHONPATH=/srv backend \
  alembic upgrade head

echo "Margin is up — http://$(curl -s ifconfig.me 2>/dev/null || echo HOST):8088"
docker compose -f docker-compose.prod.yml ps
