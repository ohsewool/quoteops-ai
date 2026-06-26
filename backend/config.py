from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_DATABASE_URL = "sqlite:///./quoteops.db"
DEFAULT_APP_ENV = "development"
DEFAULT_ALLOWED_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_DEMO_ADMIN_EMAIL = "admin@quoteops.local"
DEFAULT_DEMO_ADMIN_PASSWORD = "quoteops-demo-admin"
SAFE_APP_ENV_LABELS = {"local", "development", "test", "staging", "production"}


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _bool_env(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL
    app_env: str = DEFAULT_APP_ENV
    allowed_origins_raw: str = DEFAULT_ALLOWED_ORIGINS
    openai_api_key: str = ""
    openai_model: str = DEFAULT_OPENAI_MODEL
    llm_enabled: bool = False
    seed_demo_admin: bool = True
    demo_admin_email: str = DEFAULT_DEMO_ADMIN_EMAIL
    demo_admin_password: str = DEFAULT_DEMO_ADMIN_PASSWORD
    enable_demo_tools: bool = False

    @property
    def allowed_origins(self) -> list[str]:
        return _split_csv(self.allowed_origins_raw)

    @property
    def normalized_app_env(self) -> str:
        value = self.app_env.strip().lower() or DEFAULT_APP_ENV
        aliases = {
            "dev": "development",
            "prod": "production",
        }
        return aliases.get(value, value)

    @property
    def safe_app_env_label(self) -> str:
        value = self.normalized_app_env
        return value if value in SAFE_APP_ENV_LABELS else "custom"

    @property
    def is_production(self) -> bool:
        return self.normalized_app_env == "production"

    @property
    def database_scheme(self) -> str:
        return urlparse(self.database_url).scheme

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite:///")

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith(("postgresql://", "postgresql+psycopg://"))

    @property
    def psycopg_database_url(self) -> str:
        if not self.is_postgres:
            raise ValueError("DATABASE_URL is not a PostgreSQL URL.")
        return self.database_url.replace("postgresql+psycopg://", "postgresql://", 1)

    def sqlite_database_path(self) -> Path:
        if not self.is_sqlite:
            raise ValueError(
                "sqlite_database_path() is available only when DATABASE_URL uses sqlite:///."
            )

        raw_path = self.database_url.replace("sqlite:///", "", 1)
        db_path = Path(raw_path)
        if db_path.is_absolute():
            return db_path
        return Path.cwd() / db_path


def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL).strip()
        or DEFAULT_DATABASE_URL,
        app_env=os.getenv("APP_ENV", os.getenv("ENVIRONMENT", DEFAULT_APP_ENV)).strip()
        or DEFAULT_APP_ENV,
        allowed_origins_raw=os.getenv("ALLOWED_ORIGINS", DEFAULT_ALLOWED_ORIGINS).strip()
        or DEFAULT_ALLOWED_ORIGINS,
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        openai_model=os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL).strip()
        or DEFAULT_OPENAI_MODEL,
        llm_enabled=_bool_env(os.getenv("LLM_ENABLED", "false")),
        seed_demo_admin=_bool_env(os.getenv("SEED_DEMO_ADMIN", "true")),
        demo_admin_email=os.getenv("DEMO_ADMIN_EMAIL", DEFAULT_DEMO_ADMIN_EMAIL).strip()
        or DEFAULT_DEMO_ADMIN_EMAIL,
        demo_admin_password=os.getenv(
            "DEMO_ADMIN_PASSWORD",
            DEFAULT_DEMO_ADMIN_PASSWORD,
        ).strip()
        or DEFAULT_DEMO_ADMIN_PASSWORD,
        enable_demo_tools=_bool_env(os.getenv("ENABLE_DEMO_TOOLS", "false")),
    )
