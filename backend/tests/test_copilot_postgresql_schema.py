from __future__ import annotations

import os

import pytest
from sqlalchemy import inspect, text

from backend.config import Settings
from backend.db import build_engine


pytestmark = pytest.mark.postgresql


@pytest.fixture
def copilot_engine():
    if os.getenv("QUOTEOPS_POSTGRES_INTEGRATION") != "1":
        pytest.skip("Requires an explicitly configured V2-only PostgreSQL integration database")
    engine = build_engine(Settings())
    try:
        yield engine
    finally:
        engine.dispose()


def test_copilot_output_schema_preserves_lineage_and_immutability(copilot_engine) -> None:
    inspector = inspect(copilot_engine)
    assert "copilot_outputs" in inspector.get_table_names()
    assert {
        "ck_copilot_outputs_supported_purpose",
        "ck_copilot_outputs_nonblank_text",
        "ck_copilot_outputs_nonblank_provider",
        "ck_copilot_outputs_nonblank_generation_mode",
        "ck_copilot_outputs_purpose_context",
    }.issubset({item["name"] for item in inspector.get_check_constraints("copilot_outputs")})
    assert {item["referred_table"] for item in inspector.get_foreign_keys("copilot_outputs")} == {
        "quotes", "quote_revisions", "pricing_checks", "price_candidates", "approval_requests", "html_reports", "users"
    }
    with copilot_engine.connect() as connection:
        trigger_names = connection.execute(
            text("SELECT tgname FROM pg_trigger WHERE tgrelid = 'copilot_outputs'::regclass AND NOT tgisinternal")
        ).scalars().all()
    assert set(trigger_names) == {"copilot_outputs_lineage_guard", "copilot_outputs_immutable"}
