"""OpenTelemetry + Prometheus setup."""

from __future__ import annotations

from app.core.config import get_settings


def setup_telemetry() -> None:
    """Initialize OpenTelemetry tracing and Prometheus metrics."""
    settings = get_settings()

    if not settings.OTEL_EXPORTER_OTLP_ENDPOINT:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        resource = Resource.create({"service.name": settings.APP_NAME})
        provider = TracerProvider(resource=resource)
        trace.set_tracer_provider(provider)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument()

    except ImportError:
        pass  # OpenTelemetry is optional


def setup_sentry() -> None:
    """Initialize Sentry error tracking."""
    settings = get_settings()

    if not settings.SENTRY_DSN:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV.value,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.1,
        )
    except ImportError:
        pass  # Sentry is optional
