from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import get_settings
from backend.db import get_connection, initialize_database


REQUIRED_TABLES = [
    "products",
    "product_options",
    "competitors",
    "competitor_prices",
    "cost_profiles",
    "price_tables",
    "price_table_items",
    "candidate_tables",
    "candidate_table_items",
    "validation_results",
    "agent_logs",
    "approvals",
    "quote_requests",
    "admin_users",
    "admin_sessions",
    "audit_logs",
    "agent_jobs",
    "agent_job_steps",
    "product_categories",
    "quantity_ladders",
    "strategy_templates",
]

DUPLICATE_KEY_CHECKS = {
    "products": "slug",
    "product_categories": "slug",
    "quantity_ladders": "slug",
    "strategy_templates": "slug",
    "admin_users": "email",
}


def detect_database_type() -> str:
    settings = get_settings()
    if settings.is_postgres:
        return "postgresql"
    if settings.is_sqlite:
        return "sqlite"
    return "unsupported"


def safe_count(connection: Any, table_name: str) -> int | None:
    try:
        row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
    except Exception:
        return None
    if row is None:
        return None
    return int(row["count"])


def find_missing_tables(connection: Any) -> list[str]:
    return [table for table in REQUIRED_TABLES if safe_count(connection, table) is None]


def find_duplicate_keys(connection: Any) -> list[str]:
    duplicates: list[str] = []
    for table_name, key_column in DUPLICATE_KEY_CHECKS.items():
        try:
            rows = connection.execute(
                f"""
                SELECT {key_column} AS key_value, COUNT(*) AS count
                FROM {table_name}
                GROUP BY {key_column}
                HAVING COUNT(*) > 1
                """
            ).fetchall()
        except Exception:
            continue
        if rows:
            duplicates.append(f"{table_name}.{key_column}")
    return duplicates


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Non-destructive QuoteOps AI database smoke check."
    )
    parser.add_argument(
        "--initialize",
        action="store_true",
        help="Run the existing safe app database initialization before checking.",
    )
    args = parser.parse_args()

    settings = get_settings()
    database_type = detect_database_type()
    configured_label = "custom" if "DATABASE_URL" in __import__("os").environ else "default sqlite"

    print(f"Database configured: {configured_label}")
    print(f"Database type: {database_type}")

    if database_type == "unsupported":
        print("Connection: skipped")
        print("Schema: unsupported DATABASE_URL")
        print("Seed data: unknown")
        print("Duplicate seed keys: unknown")
        print("Secrets exposed: no")
        return 1

    if args.initialize:
        try:
            initialize_database()
            print("Initialization: ok")
        except Exception as exc:
            print("Initialization: failed")
            print(f"Error type: {exc.__class__.__name__}")
            print("Secrets exposed: no")
            return 1
    else:
        print("Initialization: skipped")

    try:
        with get_connection() as connection:
            connection.execute("SELECT 1 AS ok").fetchone()
            print("Connection: ok")

            missing_tables = find_missing_tables(connection)
            if missing_tables:
                print(f"Schema: missing {len(missing_tables)} table(s)")
                print("Missing tables: " + ", ".join(missing_tables))
                print("Seed data: unknown")
                print("Duplicate seed keys: unknown")
                print("Secrets exposed: no")
                return 1
            print("Schema: ok")

            product_count = safe_count(connection, "products") or 0
            competitor_count = safe_count(connection, "competitors") or 0
            cost_profile_count = safe_count(connection, "cost_profiles") or 0
            price_table_count = safe_count(connection, "price_tables") or 0
            admin_count = safe_count(connection, "admin_users") or 0

            seed_present = product_count > 0 and competitor_count > 0 and cost_profile_count > 0
            print("Seed data: present" if seed_present else "Seed data: missing")
            print(f"Products: {product_count}")
            print(f"Competitors: {competitor_count}")
            print(f"Cost profiles: {cost_profile_count}")
            print(f"Price tables: {price_table_count}")
            print(f"Admin users: {admin_count}")

            duplicate_keys = find_duplicate_keys(connection)
            if duplicate_keys:
                print("Duplicate seed keys: " + ", ".join(duplicate_keys))
                print("Secrets exposed: no")
                return 1
            print("Duplicate seed keys: none")
            print("Secrets exposed: no")
            return 0 if seed_present else 1
    except Exception as exc:
        print("Connection: failed")
        print(f"Error type: {exc.__class__.__name__}")
        print("Schema: unknown")
        print("Seed data: unknown")
        print("Duplicate seed keys: unknown")
        print("Secrets exposed: no")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
