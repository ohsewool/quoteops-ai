from __future__ import annotations

import os

import pytest
from sqlalchemy import inspect, text

from backend.config import Settings
from backend.db import build_engine

pytestmark = pytest.mark.postgresql


@pytest.mark.skipif(
    os.getenv("QUOTEOPS_POSTGRES_INTEGRATION") != "1",
    reason="Requires an explicitly configured V2-only PostgreSQL integration database",
)
def test_postgresql_foundation_schema_is_available_after_alembic_upgrade() -> None:
    settings = Settings(_env_file=None)
    engine = build_engine(settings)
    try:
        assert engine.dialect.name == "postgresql"
        with engine.connect() as connection:
            assert connection.execute(text("SELECT 1")).scalar_one() == 1
        tables = set(inspect(engine).get_table_names())
        assert {"users", "audit_events"}.issubset(tables)
    finally:
        engine.dispose()
