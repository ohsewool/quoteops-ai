from __future__ import annotations

import os

import pytest
from sqlalchemy import inspect, text

from backend.config import Settings
from backend.db import build_engine


pytestmark = pytest.mark.postgresql


@pytest.fixture
def approval_engine():
    if os.getenv("QUOTEOPS_POSTGRES_INTEGRATION") != "1":
        pytest.skip("Requires an explicitly configured V2-only PostgreSQL integration database")
    engine = build_engine(Settings())
    try:
        yield engine
    finally:
        engine.dispose()


def test_approval_schema_preserves_quote_candidate_lineage_and_decision_guards(approval_engine) -> None:
    inspector = inspect(approval_engine)
    assert {"approval_requests", "approval_decisions"}.issubset(set(inspector.get_table_names()))
    assert {
        "ck_approval_requests_positive_quote_version",
        "ck_approval_requests_nonnegative_candidate_price",
        "ck_approval_requests_nonnegative_candidate_profit",
        "ck_approval_requests_valid_candidate_margin",
        "ck_approval_requests_currency_krw",
        "ck_approval_requests_positive_version",
        "ck_approval_requests_nonblank_request_reason",
    }.issubset({item["name"] for item in inspector.get_check_constraints("approval_requests")})
    assert {
        "ck_approval_decisions_terminal_decision",
        "ck_approval_decisions_rejection_reason",
    }.issubset({item["name"] for item in inspector.get_check_constraints("approval_decisions")})
    assert {item["referred_table"] for item in inspector.get_foreign_keys("approval_requests")} == {
        "quotes",
        "quote_revisions",
        "pricing_checks",
        "price_candidates",
        "users",
    }
    assert {item["referred_table"] for item in inspector.get_foreign_keys("approval_decisions")} == {
        "approval_requests",
        "quote_revisions",
        "users",
    }
    request_unique_constraints = {item["name"] for item in inspector.get_unique_constraints("approval_requests")}
    decision_unique_constraints = {item["name"] for item in inspector.get_unique_constraints("approval_decisions")}
    assert "uq_approval_requests_pricing_candidate" in request_unique_constraints
    assert "uq_approval_decisions_request" in decision_unique_constraints

    with approval_engine.connect() as connection:
        numeric_columns = connection.execute(
            text(
                "SELECT table_name, column_name, numeric_precision, numeric_scale "
                "FROM information_schema.columns "
                "WHERE table_name = 'approval_requests' AND data_type = 'numeric'"
            )
        ).mappings().all()
        trigger_rows = connection.execute(
            text(
                "SELECT tgname FROM pg_trigger WHERE tgrelid IN "
                "('approval_requests'::regclass, 'approval_decisions'::regclass) "
                "AND NOT tgisinternal"
            )
        ).scalars().all()
        enum_values = connection.execute(
            text(
                "SELECT enumlabel FROM pg_enum "
                "WHERE enumtypid = 'approval_status'::regtype ORDER BY enumsortorder"
            )
        ).scalars().all()
    assert {(row["numeric_precision"], row["numeric_scale"]) for row in numeric_columns} == {(18, 2), (9, 6)}
    assert set(trigger_rows) == {
        "approval_requests_transition_guard",
        "approval_requests_immutable_delete",
        "approval_decisions_immutable",
    }
    assert enum_values == ["pending", "approved", "rejected", "cancelled"]
