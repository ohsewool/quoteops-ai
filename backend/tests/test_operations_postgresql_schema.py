from __future__ import annotations

import os

import pytest
from sqlalchemy import text

from backend.config import Settings
from backend.db import build_engine


pytestmark = pytest.mark.postgresql


def test_demo_run_schema_has_v2_09_constraints_and_owner_fk() -> None:
    if os.getenv("QUOTEOPS_POSTGRES_INTEGRATION") != "1":
        pytest.skip("Requires an explicitly configured V2-only PostgreSQL integration database")
    engine = build_engine(Settings())
    try:
        with engine.connect() as connection:
            table_exists = connection.scalar(text("SELECT to_regclass('public.demo_runs') IS NOT NULL"))
            constraints = set(
                connection.execute(
                    text("SELECT conname FROM pg_constraint WHERE conrelid = 'demo_runs'::regclass")
                ).scalars()
            )
            owner_fk = connection.scalar(
                text(
                    "SELECT count(*) FROM pg_constraint "
                    "WHERE conrelid = 'demo_runs'::regclass AND contype = 'f' "
                    "AND pg_get_constraintdef(oid) LIKE '%owner_user_id%users%RESTRICT%'"
                )
            )
        assert table_exists is True
        assert {
            "ck_demo_runs_nonnegative_current_step",
            "ck_demo_runs_current_step_in_range",
            "ck_demo_runs_positive_version",
        }.issubset(constraints)
        assert owner_fk == 1
    finally:
        engine.dispose()
