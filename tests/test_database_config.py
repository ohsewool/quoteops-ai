import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import (
    DEFAULT_DATABASE_URL,
    get_database_type,
    get_database_url,
    get_safe_database_label,
    mask_database_url,
    normalize_database_url,
)
from backend.db import get_engine_kwargs


def test_missing_database_url_defaults_to_sqlite(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert get_database_url() == DEFAULT_DATABASE_URL


def test_sqlite_database_type_is_detected_correctly():
    assert get_database_type("sqlite:///./quoteops.db") == "sqlite"


def test_postgresql_urls_are_detected_correctly():
    assert get_database_type("postgresql://user:pass@example.com:5432/quoteops") == "postgresql"
    assert (
        get_database_type("postgresql+psycopg://user:pass@example.com:5432/quoteops")
        == "postgresql"
    )
    assert (
        get_database_type("postgresql+psycopg2://user:pass@example.com:5432/quoteops")
        == "postgresql"
    )


def test_postgres_scheme_is_normalized_safely():
    raw = "postgres://user:secret@example.com:5432/quoteops"

    assert normalize_database_url(raw) == "postgresql://user:secret@example.com:5432/quoteops"
    assert get_database_url(raw).startswith("postgresql://")


def test_postgresql_database_url_is_masked_without_credentials():
    safe = mask_database_url("postgresql://user:secret@example.com:5432/quoteops")

    assert safe == "postgresql://***:***@example.com:5432/quoteops"
    assert "user" not in safe
    assert "secret" not in safe


def test_safe_database_label_does_not_return_raw_postgres_password():
    safe = get_safe_database_label("postgres://user:raw-password@example.com/quoteops")

    assert safe.startswith("postgresql://***:***@")
    assert "raw-password" not in safe


def test_postgresql_engine_config_does_not_use_sqlite_connect_args():
    kwargs = get_engine_kwargs("postgresql://user:pass@example.com:5432/quoteops")

    assert kwargs == {"pool_pre_ping": True}
    assert "connect_args" not in kwargs


def test_sqlite_engine_config_remains_test_friendly():
    kwargs = get_engine_kwargs("sqlite:///./quoteops.db")

    assert kwargs["connect_args"] == {"check_same_thread": False}


def test_env_example_exists_and_does_not_contain_real_secrets():
    env_example = Path(__file__).resolve().parents[1] / ".env.example"
    text = env_example.read_text(encoding="utf-8")

    assert "DATABASE_URL=sqlite:///./quoteops.db" in text
    assert "# DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME" in text
    assert "gho_" not in text
    assert "sk-" not in text
    assert "raw-password" not in text
