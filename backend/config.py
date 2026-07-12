"""Strict, secret-safe configuration for the clean V2 repository."""

from __future__ import annotations

from enum import StrEnum
from functools import cached_property
from typing import Annotated

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


DEFAULT_DATABASE_URL = "postgresql+psycopg://quoteops_v2:CHANGE_ME@localhost:5432/quoteops_v2"


class Environment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Configuration with secure production defaults and no implicit database."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="QUOTEOPS_",
        extra="ignore",
    )

    environment: Environment = Environment.LOCAL
    database_url: str = DEFAULT_DATABASE_URL
    test_database_url: str | None = None
    cors_origins: Annotated[tuple[str, ...], NoDecode] = ("http://localhost:5173",)
    auth_secret: SecretStr | None = None
    auth_issuer: str = "quoteops-ai-v2"
    auth_token_ttl_minutes: int = 480
    demo_enabled: bool = False
    docs_enabled: bool = True
    openapi_enabled: bool = True

    @field_validator("database_url", "test_database_url")
    @classmethod
    def require_postgresql_url(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not value.startswith(("postgresql://", "postgresql+psycopg://")):
            raise ValueError("V2 database URLs must target PostgreSQL")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> tuple[str, ...]:
        if isinstance(value, str):
            return tuple(origin.strip() for origin in value.split(",") if origin.strip())
        if isinstance(value, (list, tuple)):
            return tuple(str(origin).strip() for origin in value if str(origin).strip())
        raise ValueError("CORS origins must be a comma-separated string or sequence")

    @field_validator("auth_token_ttl_minutes")
    @classmethod
    def require_positive_token_ttl(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Authentication token TTL must be positive")
        return value

    @model_validator(mode="after")
    def enforce_environment_policy(self) -> "Settings":
        if not self.cors_origins:
            raise ValueError("At least one CORS origin is required")
        if "*" in self.cors_origins:
            raise ValueError("Wildcard CORS is prohibited in every V2 environment")
        if self.test_database_url and self.test_database_url == self.database_url:
            raise ValueError("Test and application databases must be distinct")
        if self.environment in {Environment.STAGING, Environment.PRODUCTION}:
            if self.demo_enabled:
                raise ValueError("Demo mode is prohibited in staging and production")
            if self.docs_enabled or self.openapi_enabled:
                raise ValueError("Staging and production docs and OpenAPI must be disabled")
            if self.auth_secret is None or self.auth_secret.get_secret_value().startswith("CHANGE_ME"):
                raise ValueError("Staging and production require a configured authentication secret")
        return self

    @cached_property
    def is_production_like(self) -> bool:
        return self.environment in {Environment.STAGING, Environment.PRODUCTION}

    @cached_property
    def database_is_configured(self) -> bool:
        return "CHANGE_ME" not in self.database_url

    def safe_summary(self) -> dict[str, object]:
        """Return only non-sensitive configuration state for diagnostics."""

        return {
            "environment": self.environment.value,
            "database_configured": self.database_is_configured,
            "docs_enabled": self.docs_enabled,
            "openapi_enabled": self.openapi_enabled,
            "demo_enabled": self.demo_enabled,
            "cors_origin_count": len(self.cors_origins),
        }
