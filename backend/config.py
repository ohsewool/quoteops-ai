import os
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


DEFAULT_DATABASE_URL = "sqlite:///./quoteops.db"
POSTGRESQL_SCHEMES = {
    "postgresql",
    "postgresql+psycopg",
    "postgresql+psycopg2",
}


@dataclass(frozen=True)
class Settings:
    database_url: str
    allowed_origins: list[str]
    openai_configured: bool
    demo_tools_enabled: bool

    @property
    def database_type(self) -> str:
        return get_database_type(self.database_url)

    @property
    def database_url_safe(self) -> str:
        return mask_database_url(self.database_url)


def get_settings() -> Settings:
    allowed_origins = os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    )
    return Settings(
        database_url=get_database_url(),
        allowed_origins=[
            origin.strip() for origin in allowed_origins.split(",") if origin.strip()
        ],
        openai_configured=bool(os.getenv("OPENAI_API_KEY")),
        demo_tools_enabled=os.getenv("DEMO_TOOLS_ENABLED", "false").lower() == "true",
    )


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
