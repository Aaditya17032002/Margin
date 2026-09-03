"""Custom exception handlers for FastAPI."""

from __future__ import annotations

from fastapi import FastAPI, Request, status
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError

from app.core.logging import get_logger

logger = get_logger()


async def validation_error_handler(request: Request, exc: ValidationError) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors()},
    )


async def integrity_error_handler(request: Request, exc: IntegrityError) -> ORJSONResponse:
    logger.warning("integrity_error", detail=str(exc.orig))
    return ORJSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Resource conflict or duplicate."},
    )


async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> ORJSONResponse:
    return ORJSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": f"Rate limit exceeded: {exc.detail}"},
    )


async def generic_error_handler(request: Request, exc: Exception) -> ORJSONResponse:
    logger.exception("unhandled_error", exc_info=exc)
    return ORJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ValidationError, validation_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(IntegrityError, integrity_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RateLimitExceeded, rate_limit_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_error_handler)
