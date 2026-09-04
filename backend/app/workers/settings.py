"""Arq worker settings — defines the task queue and worker configuration."""

from __future__ import annotations

from arq.connections import RedisSettings

from app.core.config import get_settings


def get_redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD or None,
        database=settings.REDIS_DB,
    )


class WorkerSettings:
    """Arq WorkerSettings — discovered by `arq app.workers.settings.WorkerSettings`."""

    functions = [
        "app.workers.run_analysis.run_analysis_task",
        "app.workers.generate_report.generate_report_task",
        "app.workers.refresh_amendment.refresh_amendment_task",
        "app.workers.check_response.check_response_task",
    ]
    redis_settings = get_redis_settings()
    max_jobs = 10
    job_timeout = 1800  # 30 minutes — o3-deep-research is a background job
    keep_result = 3600
    poll_delay = 0.5
