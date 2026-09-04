"""Margin backend — FastAPI app factory with lifespan management."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import get_settings
from app.core.deps import close_redis, init_redis
from app.core.queue import close_queue, init_queue
from app.core.exceptions import register_exception_handlers
from app.core.logging import RequestIdMiddleware, setup_logging, get_logger
from app.core.rate_limit import limiter
from app.db.base import dispose_db, init_db

logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    settings = get_settings()
    setup_logging()
    logger.info("starting", app=settings.APP_NAME, env=settings.APP_ENV.value)

    # Init database
    await init_db()
    logger.info("database_connected")

    # Init Redis
    await init_redis(settings.REDIS_URL)
    logger.info("redis_connected")

    # Init the task queue the API enqueues onto
    try:
        await init_queue()
        logger.info("queue_connected")
    except Exception as exc:  # noqa: BLE001 — the API still serves reads without a worker
        logger.error("queue_connect_failed", error=str(exc))

    yield

    # Shutdown
    await close_queue()
    await close_redis()
    await dispose_db()
    logger.info("shutdown_complete")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        docs_url=f"{settings.API_V1_PREFIX}/docs",
        redoc_url=f"{settings.API_V1_PREFIX}/redoc",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIdMiddleware)

    # Rate limiter
    app.state.limiter = limiter

    # Exception handlers
    register_exception_handlers(app)

    # ── Routers ──────────────────────────────────────────────────────────
    from app.api.v1 import (
        auth,
        analyses,
        documents,
        ingest,
        contradictions,
        matrix,
        questions,
        response,
        reviews,
        findings,
        versions,
        notifications,
        team,
        integrations,
        templates,
        knowledge,
        preferences,
        reports,
        deadlines,
        activity,
        search,
        verification,
        governance,
    )

    prefix = settings.API_V1_PREFIX
    app.include_router(auth.router, prefix=prefix)
    app.include_router(analyses.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(ingest.router, prefix=prefix)
    app.include_router(matrix.router, prefix=prefix)
    app.include_router(contradictions.router, prefix=prefix)
    app.include_router(response.router, prefix=prefix)
    app.include_router(reviews.router, prefix=prefix)
    app.include_router(questions.router, prefix=prefix)
    app.include_router(findings.router, prefix=prefix)
    app.include_router(versions.router, prefix=prefix)
    app.include_router(notifications.router, prefix=prefix)
    app.include_router(team.router, prefix=prefix)
    app.include_router(integrations.router, prefix=prefix)
    app.include_router(templates.router, prefix=prefix)
    app.include_router(knowledge.router, prefix=prefix)
    app.include_router(preferences.router, prefix=prefix)
    app.include_router(reports.router, prefix=prefix)
    app.include_router(deadlines.router, prefix=prefix)
    app.include_router(activity.router, prefix=prefix)
    app.include_router(search.router, prefix=prefix)
    app.include_router(verification.router, prefix=prefix)
    app.include_router(governance.router, prefix=prefix)

    # ── Health / Ready / Metrics ─────────────────────────────────────────

    @app.get("/health", tags=["ops"])
    async def health():
        return {"status": "ok"}

    @app.get("/ready", tags=["ops"])
    async def ready():
        """Readiness check — verifies DB and Redis are reachable."""
        checks = {}
        try:
            from app.db.base import get_engine
            async with get_engine().begin() as conn:
                from sqlalchemy import text
                await conn.execute(text("SELECT 1"))
            checks["db"] = "ok"
        except Exception as e:
            checks["db"] = f"error: {e}"

        try:
            from app.core.deps import get_redis
            redis = await get_redis()
            await redis.ping()
            checks["redis"] = "ok"
        except Exception as e:
            checks["redis"] = f"error: {e}"

        all_ok = all(v == "ok" for v in checks.values())
        return ORJSONResponse(
            content={"status": "ready" if all_ok else "degraded", "checks": checks},
            status_code=200 if all_ok else 503,
        )

    @app.get("/metrics", tags=["ops"])
    async def metrics():
        """Prometheus metrics endpoint."""
        try:
            from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
            from starlette.responses import Response
            return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
        except ImportError:
            return {"detail": "prometheus_client not installed"}

    return app


# Gunicorn / Uvicorn entry point
app = create_app()
