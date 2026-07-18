from __future__ import annotations

import os

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import DBAPIError

from backend.config import Settings
from backend.db import build_engine


pytestmark = pytest.mark.postgresql


@pytest.fixture
def pricing_engine():
    if os.getenv("QUOTEOPS_POSTGRES_INTEGRATION") != "1":
        pytest.skip("Requires an explicitly configured V2-only PostgreSQL integration database")
    engine = build_engine(Settings())
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE TABLE price_validation_checks, price_validation_results, price_candidate_lines, "
                    "price_candidates, pricing_checks, competitor_references, competitors, cost_profiles, products, "
                    "quote_revision_lines, quote_revisions, quote_lines, quotes, audit_events, customer_requests, users "
                    "RESTART IDENTITY CASCADE"
                )
            )
        yield engine
    finally:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE TABLE price_validation_checks, price_validation_results, price_candidate_lines, "
                    "price_candidates, pricing_checks, competitor_references, competitors, cost_profiles, products, "
                    "quote_revision_lines, quote_revisions, quote_lines, quotes, audit_events, customer_requests, users "
                    "RESTART IDENTITY CASCADE"
                )
            )
        engine.dispose()


def test_pricing_schema_has_decimal_constraints_source_fks_and_immutable_evidence(pricing_engine) -> None:
    inspector = inspect(pricing_engine)
    expected_tables = {
        "products",
        "cost_profiles",
        "competitors",
        "competitor_references",
        "pricing_checks",
        "price_candidates",
        "price_candidate_lines",
        "price_validation_results",
        "price_validation_checks",
    }
    assert expected_tables.issubset(set(inspector.get_table_names()))
    assert {
        "ck_cost_profiles_nonnegative_material_cost",
        "ck_cost_profiles_nonnegative_labor_cost",
        "ck_cost_profiles_nonnegative_overhead_cost",
        "ck_cost_profiles_valid_target_margin",
        "ck_cost_profiles_positive_version",
    }.issubset({item["name"] for item in inspector.get_check_constraints("cost_profiles")})
    assert {
        "ck_pricing_checks_positive_quote_version",
        "ck_pricing_checks_valid_selected_margin",
        "ck_pricing_checks_valid_minimum_margin",
        "ck_pricing_checks_currency_krw",
        "ck_pricing_checks_supported_strategy",
    }.issubset({item["name"] for item in inspector.get_check_constraints("pricing_checks")})
    assert {item["referred_table"] for item in inspector.get_foreign_keys("pricing_checks")} == {
        "quotes",
        "quote_revisions",
        "users",
    }
    assert {item["referred_table"] for item in inspector.get_foreign_keys("price_candidate_lines")} == {
        "price_candidates",
        "quote_revision_lines",
    }
    indexes = {item["name"] for item in inspector.get_indexes("cost_profiles")}
    assert "uq_cost_profiles_one_active_per_product" in indexes

    with pricing_engine.connect() as connection:
        numeric_columns = connection.execute(
            text(
                "SELECT table_name, column_name, numeric_precision, numeric_scale "
                "FROM information_schema.columns "
                "WHERE table_name IN ('cost_profiles', 'pricing_checks', 'price_candidates', 'price_candidate_lines', 'price_validation_results') "
                "AND data_type = 'numeric'"
            )
        ).mappings().all()
        trigger_rows = connection.execute(
            text(
                "SELECT tgname FROM pg_trigger WHERE tgrelid IN "
                "('pricing_checks'::regclass, 'price_candidates'::regclass, 'price_candidate_lines'::regclass, "
                "'price_validation_results'::regclass, 'price_validation_checks'::regclass) "
                "AND NOT tgisinternal"
            )
        ).scalars().all()
    assert {(row["numeric_precision"], row["numeric_scale"]) for row in numeric_columns} == {(18, 2), (9, 6)}
    assert set(trigger_rows) == {
        "pricing_checks_immutable",
        "price_candidates_immutable",
        "price_candidate_lines_immutable",
        "price_validation_results_immutable",
        "price_validation_checks_immutable",
    }

    with pricing_engine.begin() as connection:
        user_id = connection.execute(
            text(
                "INSERT INTO users (username, display_name, password_hash, role, active) "
                "VALUES ('pricing-owner', 'Pricing Owner', 'not-used', 'manager', true) RETURNING id"
            )
        ).scalar_one()
        product_id = connection.execute(
            text(
                "INSERT INTO products (code, name, active, created_by_user_id, version) "
                "VALUES ('a3_flyer', 'A3 Flyer', true, :user_id, 1) RETURNING id"
            ),
            {"user_id": user_id},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO cost_profiles "
                "(product_id, material_cost, labor_cost, overhead_cost, target_margin_rate, active, created_by_user_id, version) "
                "VALUES (:product_id, 1.00, 1.00, 1.00, 0.350000, true, :user_id, 1)"
            ),
            {"product_id": product_id, "user_id": user_id},
        )
        with pytest.raises(DBAPIError):
            with connection.begin_nested():
                connection.execute(
                    text(
                        "INSERT INTO cost_profiles "
                        "(product_id, material_cost, labor_cost, overhead_cost, target_margin_rate, active, created_by_user_id, version) "
                        "VALUES (:product_id, 2.00, 2.00, 2.00, 0.350000, true, :user_id, 1)"
                    ),
                    {"product_id": product_id, "user_id": user_id},
                )
