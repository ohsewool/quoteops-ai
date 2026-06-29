import os
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


DEFAULT_DATABASE_URL = "sqlite:///./quoteops.db"
DEFAULT_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
POSTGRESQL_SCHEMES = {
    "postgresql",
    "postgresql+psycopg",
    "postgresql+psycopg2",
}


@dataclass(frozen=True)
class Settings:
    database_url: str
    cors_origins: list[str]
    environment: str
    openai_configured: bool
    demo_tools_enabled: bool

    @property
    def allowed_origins(self) -> list[str]:
        return self.cors_origins

    @property
    def database_type(self) -> str:
        return get_database_type(self.database_url)

    @property
    def database_url_safe(self) -> str:
        return mask_database_url(self.database_url)

    @property
    def cors_origins_configured(self) -> bool:
        return bool(self.cors_origins)

    @property
    def cors_origin_count(self) -> int:
        return len(self.cors_origins)


def get_settings() -> Settings:
    environment = get_environment()
    return Settings(
        database_url=get_database_url(),
        cors_origins=get_cors_origins(environment=environment),
        environment=environment,
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        demo_tools_enabled=_bool_env(
            os.getenv(
                "QUOTEOPS_DEMO_TOOLS_ENABLED",
                os.getenv("DEMO_TOOLS_ENABLED", "false"),
            )
        ),
    )


def _bool_env(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "on"}


def get_environment(raw_environment: str | None = None) -> str:
    resolved = (
        raw_environment
        if raw_environment is not None
        else os.getenv("QUOTEOPS_ENV", "local")
    )
    return resolved.strip() or "local"


def get_cors_origins(
    raw_origins: str | None = None,
    *,
    environment: str | None = None,
) -> list[str]:
    resolved_environment = get_environment(environment)
    configured = raw_origins
    if configured is None:
        configured = os.getenv("QUOTEOPS_CORS_ORIGINS")
    if configured is None:
        configured = os.getenv("ALLOWED_ORIGINS")
    if configured is None:
        origins = DEFAULT_CORS_ORIGINS
    else:
        origins = [origin.strip() for origin in configured.split(",")]

    cleaned = _dedupe_preserving_order([origin for origin in origins if origin])
    if resolved_environment.lower() == "production":
        return [origin for origin in cleaned if origin != "*"]
    return cleaned


def is_demo_tools_enabled(raw_value: str | None = None) -> bool:
    if raw_value is not None:
        return _bool_env(raw_value)
    return _bool_env(
        os.getenv(
            "QUOTEOPS_DEMO_TOOLS_ENABLED",
            os.getenv("DEMO_TOOLS_ENABLED", "false"),
        )
    )


def get_safe_config_summary() -> dict[str, int | str | bool]:
    settings = get_settings()
    return {
        "environment": settings.environment,
        "database_type": settings.database_type,
        "cors_origins_configured": settings.cors_origins_configured,
        "cors_origin_count": settings.cors_origin_count,
        "demo_tools_enabled": settings.demo_tools_enabled,
        "openai_configured": settings.openai_configured,
    }


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def get_database_url(raw_url: str | None = None) -> str:
    resolved = raw_url if raw_url is not None else os.getenv("DATABASE_URL")
    if not resolved:
        return DEFAULT_DATABASE_URL
    return normalize_database_url(resolved.strip())


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return "postgresql://" + database_url.removeprefix("postgres://")
    return database_url


def get_database_type(database_url: str | None = None) -> str:
    resolved = get_database_url(database_url)
    scheme = urlsplit(resolved).scheme
    if scheme.startswith("sqlite"):
        return "sqlite"
    if scheme in POSTGRESQL_SCHEMES:
        return "postgresql"
    return "other"


def get_safe_database_label(database_url: str | None = None) -> str:
    return mask_database_url(get_database_url(database_url))


def mask_database_url(database_url: str | None = None) -> str:
    resolved = get_database_url(database_url)
    if get_database_type(resolved) != "postgresql":
        return resolved

    parsed = urlsplit(resolved)
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    database_name = parsed.path or ""
    safe_netloc = f"***:***@{host}{port}" if host else "***"
    return urlunsplit((parsed.scheme, safe_netloc, database_name, "", ""))
