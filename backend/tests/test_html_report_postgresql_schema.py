from __future__ import annotations

import os

import pytest
from sqlalchemy import inspect, text

from backend.config import Settings
from backend.db import build_engine


pytestmark = pytest.mark.postgresql


@pytest.fixture
def report_engine():
    if os.getenv("QUOTEOPS_POSTGRES_INTEGRATION") != "1":
        pytest.skip("Requires an explicitly configured V2-only PostgreSQL integration database")
    engine = build_engine(Settings())
    try:
        yield engine
    finally:
        engine.dispose()


def test_html_report_schema_requires_approved_lineage_and_immutable_artifacts(report_engine) -> None:
    inspector = inspect(report_engine)
    assert "html_reports" in inspector.get_table_names()
    assert {
        "ck_html_reports_supported_type",
        "ck_html_reports_nonblank_title",
        "ck_html_reports_nonblank_summary",
        "ck_html_reports_nonempty_content",
        "ck_html_reports_content_sha256",
    }.issubset({item["name"] for item in inspector.get_check_constraints("html_reports")})
    assert {item["referred_table"] for item in inspector.get_foreign_keys("html_reports")} == {
        "quotes",
        "quote_revisions",
        "approval_requests",
        "approval_decisions",
        "html_reports",
        "users",
    }
    with report_engine.connect() as connection:
        trigger_rows = connection.execute(
            text(
                "SELECT tgname FROM pg_trigger WHERE tgrelid = 'html_reports'::regclass "
                "AND NOT tgisinternal"
            )
        ).scalars().all()
        columns = connection.execute(
            text(
                "SELECT column_name, data_type FROM information_schema.columns "
                "WHERE table_name = 'html_reports'"
            )
        ).mappings().all()
    assert set(trigger_rows) == {"html_reports_lineage_guard", "html_reports_immutable"}
    assert {row["column_name"] for row in columns}.issuperset(
        {
            "source_quote_revision_id",
            "approval_request_id",
            "approval_decision_id",
            "predecessor_report_id",
            "snapshot_json",
            "html_content",
            "content_sha256",
        }
    )
    assert next(row["data_type"] for row in columns if row["column_name"] == "snapshot_json") == "json"
