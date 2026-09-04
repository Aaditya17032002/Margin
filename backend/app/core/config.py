"""Margin backend — pydantic-settings configuration.

12-factor: every knob is an env var with a sensible default for local dev.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEV = "dev"
    STAGING = "staging"
    PROD = "prod"


class Settings(BaseSettings):
    """Central configuration — all values overridable via environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "Margin"
    APP_ENV: Environment = Environment.DEV
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    ALLOWED_ORIGINS: list[str] = Field(default=["http://localhost:3000"])

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            text = value.strip()
            if not text:
                return []
            if text.startswith("["):
                import json

                return json.loads(text)
            return [part.strip() for part in text.split(",") if part.strip()]
        return value
    LOG_LEVEL: str = "DEBUG"

    # ── Auth / JWT ───────────────────────────────────────────────────────
    SECRET_KEY: str = "CHANGE-ME-in-production-use-openssl-rand-hex-64"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Microsoft OAuth (MSAL) ───────────────────────────────────────────
    MS_CLIENT_ID: str = ""
    MS_CLIENT_SECRET: str = ""
    MS_TENANT_ID: str = ""
    MS_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/microsoft/callback"

    # ── Database ─────────────────────────────────────────────────────────
    # Prefer DATABASE_URL (e.g. Neon). Otherwise assemble from discrete parts.
    DATABASE_URL_OVERRIDE: str | None = Field(default=None, validation_alias="DATABASE_URL")
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "margin"
    DB_PASSWORD: str = "margin"
    DB_NAME: str = "margin"
    # Neon / managed Postgres require TLS; local Docker usually does not.
    DB_SSL: bool = False

    @staticmethod
    def _normalize_db_url(url: str, *, driver: Literal["asyncpg", "psycopg"] | None = "asyncpg") -> str:
        """Accept postgres:// / postgresql:// / +asyncpg URLs; strip libpq-only query params."""
        from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

        cleaned = url.strip()
        if cleaned.startswith("postgres://"):
            cleaned = "postgresql://" + cleaned[len("postgres://") :]

        parsed = urlparse(cleaned)
        scheme = parsed.scheme
        if driver == "asyncpg":
            if scheme in ("postgresql", "postgres"):
                scheme = "postgresql+asyncpg"
            elif scheme == "postgresql+psycopg2":
                scheme = "postgresql+asyncpg"
        elif driver is None:
            # Sync URL for Alembic / tooling
            if "+asyncpg" in scheme:
                scheme = "postgresql"
            elif scheme in ("postgres",):
                scheme = "postgresql"

        # asyncpg does not honour sslmode / channel_binding in the URL the same way libpq does.
        query = [
            (k, v)
            for k, v in parse_qsl(parsed.query, keep_blank_values=True)
            if k.lower() not in {"sslmode", "channel_binding", "ssl"}
        ]
        return urlunparse(parsed._replace(scheme=scheme, query=urlencode(query)))

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            return self._normalize_db_url(self.DATABASE_URL_OVERRIDE, driver="asyncpg")
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL_SYNC(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            return self._normalize_db_url(self.DATABASE_URL_OVERRIDE, driver=None)
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_ssl(self) -> bool:
        if self.DB_SSL:
            return True
        if not self.DATABASE_URL_OVERRIDE:
            return False
        lower = self.DATABASE_URL_OVERRIDE.lower()
        return "sslmode=require" in lower or "neon.tech" in lower or "ssl=true" in lower

    # ── Redis ────────────────────────────────────────────────────────────
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # ── Provider selection ───────────────────────────────────────────────
    PROVIDER_MODE: Literal["mock", "azure"] = "mock"

    # ── Azure OpenAI (Sweden Central — chat + embeddings) ────────────────
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2025-01-01-preview"
    # Routing / cheap fields (orchestration)
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"
    # In-document extraction (specialist agents)
    AZURE_OPENAI_DEPLOYMENT_EXTRACT: str = "gpt-5.2"
    # Critic / verifier (citation checks — strongest reasoning)
    AZURE_OPENAI_DEPLOYMENT_VERIFIER: str = "gpt-5.2"
    # Embeddings (pgvector) — may use a separate key on the same resource
    AZURE_EMBEDDING_DEPLOYMENT: str = "text-embedding-3-large"
    AZURE_EMBEDDING_API_KEY: str = ""
    AZURE_EMBEDDING_API_VERSION: str = "2024-12-01-preview"

    # ── Azure Deep Research (Norway East — o3-deep-research + Bing) ──────
    AZURE_DEEP_RESEARCH_ENDPOINT: str = ""
    AZURE_DEEP_RESEARCH_INFERENCE_ENDPOINT: str = ""
    AZURE_DEEP_RESEARCH_API_KEY: str = ""
    AZURE_DEEP_RESEARCH_DEPLOYMENT: str = "o3-deep-research"
    AZURE_DEEP_RESEARCH_REGION: str = "norwayeast"
    AZURE_DEEP_RESEARCH_API_VERSION: str = "2025-01-01-preview"
    #: The deployment is capacity-limited and a rejection often arrives as a
    #: background job that fails minutes later, so the whole job is retried.
    AZURE_DEEP_RESEARCH_MAX_ATTEMPTS: int = 3
    AZURE_DEEP_RESEARCH_RETRY_SECONDS: float = 30.0

    AZURE_DOCINTEL_ENDPOINT: str = ""
    AZURE_DOCINTEL_KEY: str = ""
    AZURE_SEARCH_ENDPOINT: str = ""
    AZURE_SEARCH_KEY: str = ""

    # ── Embedding ────────────────────────────────────────────────────────
    EMBEDDING_DIM: int = 1536

    # ── Reports ──────────────────────────────────────────────────────────
    REPORTS_DIR: str = "/srv/reports"

    # ── Uploads ──────────────────────────────────────────────────────────
    UPLOADS_DIR: str = "/srv/uploads"
    MAX_UPLOAD_BYTES: int = 64 * 1024 * 1024

    # ── Rate limits ──────────────────────────────────────────────────────
    RATE_LIMIT_AUTH: str = "5/minute"
    RATE_LIMIT_RUN: str = "10/minute"
    RATE_LIMIT_EXPORT: str = "10/minute"

    # ── Observability ────────────────────────────────────────────────────
    SENTRY_DSN: str = ""
    OTEL_EXPORTER_OTLP_ENDPOINT: str = ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
