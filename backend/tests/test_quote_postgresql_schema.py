from __future__ import annotations

import os

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

from backend.config import Settings
from backend.db import build_engine


pytestmark = pytest.mark.postgresql


def _truncate_quote_domain(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE quote_revision_lines, quote_revisions, quote_lines, quotes, "
                "audit_events, customer_requests, users RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def quote_engine():
    if os.getenv("QUOTEOPS_POSTGRES_INTEGRATION") != "1":
        pytest.skip("Requires an explicitly configured V2-only PostgreSQL integration database")
    engine = build_engine(Settings())
    try:
        _truncate_quote_domain(engine)
        yield engine
    finally:
        _truncate_quote_domain(engine)
        engine.dispose()


def test_quote_schema_uses_numeric_constraints_and_immutable_revisions(quote_engine) -> None:
    inspector = inspect(quote_engine)
    expected_tables = {"quotes", "quote_lines", "quote_revisions", "quote_revision_lines"}
    assert expected_tables.issubset(set(inspector.get_table_names()))

    quote_constraints = {item["name"] for item in inspector.get_check_constraints("quotes")}
    assert {
        "ck_quotes_positive_request_quantity",
        "ck_quotes_positive_source_request_version",
        "ck_quotes_positive_version",
        "ck_quotes_nonnegative_current_revision_number",
        "ck_quotes_nonnegative_total_amount",
        "ck_quotes_currency_krw",
    }.issubset(quote_constraints)
    quote_line_constraints = {item["name"] for item in inspector.get_check_constraints("quote_lines")}
    assert {
        "ck_quote_lines_positive_position",
        "ck_quote_lines_positive_quantity",
        "ck_quote_lines_nonnegative_unit_price",
        "ck_quote_lines_nonnegative_line_total",
    }.issubset(quote_line_constraints)
    revision_constraints = {item["name"] for item in inspector.get_check_constraints("quote_revisions")}
    assert {
        "ck_quote_revisions_positive_revision_number",
        "ck_quote_revisions_positive_quote_version",
        "ck_quote_revisions_positive_request_quantity",
        "ck_quote_revisions_positive_source_request_version",
        "ck_quote_revisions_nonnegative_line_count",
        "ck_quote_revisions_nonnegative_total_amount",
        "ck_quote_revisions_currency_krw",
    }.issubset(revision_constraints)
    assert {item["referred_table"] for item in inspector.get_foreign_keys("quotes")} == {
        "customer_requests",
        "users",
    }
    assert {item["referred_table"] for item in inspector.get_foreign_keys("quote_revisions")} == {
        "quotes",
        "users",
    }
    assert {item["referred_table"] for item in inspector.get_foreign_keys("quote_revision_lines")} == {
        "quote_revisions"
    }

    with quote_engine.connect() as connection:
        numeric_columns = connection.execute(
            text(
                "SELECT table_name, column_name, numeric_precision, numeric_scale "
                "FROM information_schema.columns "
                "WHERE table_name IN ('quotes', 'quote_lines', 'quote_revisions', 'quote_revision_lines') "
                "AND column_name IN ('total_amount', 'unit_price', 'line_total')"
            )
        ).mappings().all()
        quote_status_values = connection.execute(
            text(
                "SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_type.oid = pg_enum.enumtypid "
                "WHERE pg_type.typname = 'quote_status' ORDER BY enumsortorder"
            )
        ).scalars().all()
        triggers = set(
            connection.execute(
                text(
                    "SELECT tgname FROM pg_trigger "
                    "WHERE tgrelid IN ('quote_revisions'::regclass, 'quote_revision_lines'::regclass) "
                    "AND NOT tgisinternal"
                )
            ).scalars()
        )
    assert {(row["numeric_precision"], row["numeric_scale"]) for row in numeric_columns} == {(18, 2)}
    assert quote_status_values == [
        "draft",
        "pricing_review",
        "blocked",
        "approval_pending",
        "approved",
        "rejected",
        "cancelled",
    ]
    assert triggers == {"quote_revisions_immutable", "quote_revision_lines_immutable"}

    with quote_engine.begin() as connection:
        user_id = connection.execute(
            text(
                "INSERT INTO users (username, display_name, password_hash, role, active) "
                "VALUES ('quote-owner', 'Quote Owner', 'not-used', 'manager', true) RETURNING id"
            )
        ).scalar_one()
        request_id = connection.execute(
            text(
                "INSERT INTO customer_requests "
                "(customer_name, product_code, quantity, status, created_by_user_id, version) "
                "VALUES ('Quote Customer', 'a3_flyer', 25, 'reviewing', :user_id, 1) RETURNING id"
            ),
            {"user_id": user_id},
        ).scalar_one()
        quote_id = connection.execute(
            text(
                "INSERT INTO quotes "
                "(customer_request_id, quote_number, title, customer_name_snapshot, request_product_code, "
                "request_quantity, source_request_version, status, currency, total_amount, formula_version, "
                "rounding_policy_version, created_by_user_id, version, current_revision_number) "
                "VALUES (:request_id, 'Q-000001', 'Initial Quote', 'Quote Customer', 'a3_flyer', 25, 1, "
                "'draft', 'KRW', 25000.00, 'quote-line-sum-v1', 'krw-half-up-v1', :user_id, 1, 1) RETURNING id"
            ),
            {"request_id": request_id, "user_id": user_id},
        ).scalar_one()
        revision_id = connection.execute(
            text(
                "INSERT INTO quote_revisions "
                "(quote_id, revision_number, quote_version, source_request_version, status, quote_number, "
                "title, customer_name_snapshot, request_product_code, request_quantity, currency, total_amount, "
                "formula_version, rounding_policy_version, line_count, created_by_user_id) "
                "VALUES (:quote_id, 1, 1, 1, 'draft', 'Q-000001', 'Initial Quote', 'Quote Customer', "
                "'a3_flyer', 25, 'KRW', 25000.00, 'quote-line-sum-v1', 'krw-half-up-v1', 1, :user_id) RETURNING id"
            ),
            {"quote_id": quote_id, "user_id": user_id},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO quote_revision_lines "
                "(quote_revision_id, position, description, product_code, quantity, unit_price, line_total, options_json) "
                "VALUES (:revision_id, 1, 'A3 Flyer', 'a3_flyer', 25, 1000.00, 25000.00, '{}'::json)"
            ),
            {"revision_id": revision_id},
        )

    with pytest.raises(DBAPIError, match="quote revisions are immutable"):
        with quote_engine.begin() as connection:
            connection.execute(
                text("UPDATE quote_revisions SET title = 'Changed' WHERE id = :revision_id"),
                {"revision_id": revision_id},
            )
