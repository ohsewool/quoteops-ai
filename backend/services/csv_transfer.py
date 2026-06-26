from __future__ import annotations

import csv
import io
import json
import sqlite3
from typing import Any

from backend.db import utc_now


COMPETITOR_PRICE_COLUMNS = [
    "competitor_name",
    "product_slug",
    "quantity",
    "option_summary",
    "price",
    "source_note",
    "collected_at",
]

COST_PROFILE_COLUMNS = [
    "product_slug",
    "quantity",
    "option_summary",
    "unit_cost",
    "fixed_cost",
    "minimum_margin_rate",
    "minimum_price",
]

PRICE_TABLE_ITEM_COLUMNS = [
    "price_table_id",
    "quantity",
    "option_summary",
    "final_price",
    "margin_rate",
]

CANDIDATE_TABLE_ITEM_COLUMNS = [
    "candidate_table_id",
    "quantity",
    "candidate_price",
    "unit_price",
    "cost_floor_price",
    "estimated_margin_rate",
    "market_lowest_price",
    "market_average_price",
    "market_highest_price",
    "decision_reason_codes",
    "warnings",
]


def _read_csv_rows(csv_text: str) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    try:
        reader = csv.DictReader(io.StringIO(csv_text.strip()))
        if not reader.fieldnames:
            return [], [{"row": 1, "field": "csv", "message": "CSV header row is required."}]
        rows = [
            {key: (value or "").strip() for key, value in row.items() if key is not None}
            for row in reader
        ]
        return rows, []
    except csv.Error as exc:
        return [], [{"row": 1, "field": "csv", "message": f"Invalid CSV: {exc}"}]


def _missing_columns(rows: list[dict[str, str]], required_columns: list[str]) -> list[str]:
    if not rows:
        return []
    columns = set(rows[0].keys())
    return [column for column in required_columns if column not in columns]


def _positive_int(value: str) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _float_value(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _product_ids_by_slug(connection: sqlite3.Connection) -> dict[str, int]:
    rows = connection.execute("SELECT id, slug FROM products").fetchall()
    return {row["slug"]: row["id"] for row in rows}


def _competitor_ids_by_name(connection: sqlite3.Connection) -> dict[str, int]:
    rows = connection.execute("SELECT id, name FROM competitors").fetchall()
    return {row["name"].strip().lower(): row["id"] for row in rows}


def _claims_sample_as_real(source_note: str) -> bool:
    note = source_note.strip().lower()
    if not note:
        return False
    risky_phrases = [
        "real market price",
        "actual market price",
        "verified market price",
        "confirmed market price",
        "real price",
    ]
    return any(phrase in note for phrase in risky_phrases) and "not real" not in note


def import_competitor_prices(connection: sqlite3.Connection, csv_text: str) -> dict[str, Any]:
    rows, errors = _read_csv_rows(csv_text)
    if rows:
        for column in _missing_columns(rows, COMPETITOR_PRICE_COLUMNS):
            errors.append({"row": 1, "field": column, "message": "Required column is missing."})

    product_ids = _product_ids_by_slug(connection)
    competitor_ids = _competitor_ids_by_name(connection)
    valid_rows: list[dict[str, Any]] = []

    if not errors:
        for index, row in enumerate(rows, start=2):
            row_errors = []
            competitor_name = row.get("competitor_name", "").strip()
            product_slug = row.get("product_slug", "").strip()
            quantity = _positive_int(row.get("quantity", ""))
            price = _float_value(row.get("price", ""))
            option_summary = row.get("option_summary", "").strip()
            source_note = row.get("source_note", "").strip()

            competitor_id = competitor_ids.get(competitor_name.lower())
            product_id = product_ids.get(product_slug)
            if competitor_id is None:
                row_errors.append({"row": index, "field": "competitor_name", "message": "Competitor must exist before import."})
            if product_id is None:
                row_errors.append({"row": index, "field": "product_slug", "message": "Product must exist before import."})
            if quantity is None:
                row_errors.append({"row": index, "field": "quantity", "message": "Quantity must be positive."})
            if price is None or price <= 0:
                row_errors.append({"row": index, "field": "price", "message": "Price must be positive."})
            if not option_summary:
                row_errors.append({"row": index, "field": "option_summary", "message": "Option summary is required."})
            if _claims_sample_as_real(source_note):
                row_errors.append({"row": index, "field": "source_note", "message": "Sample prices must not be claimed as real market prices."})

            if row_errors:
                errors.extend(row_errors)
                continue

            valid_rows.append(
                {
                    "competitor_id": competitor_id,
                    "product_id": product_id,
                    "quantity": quantity,
                    "option_summary": option_summary,
                    "price": price,
                    "source_note": source_note,
                    "collected_at": row.get("collected_at", "").strip() or utc_now(),
                }
            )

    inserted_count = 0
    if not errors:
        now = utc_now()
        connection.executemany(
            """
            INSERT INTO competitor_prices (
                competitor_id, product_id, quantity, option_summary, price,
                source_note, collected_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["competitor_id"],
                    row["product_id"],
                    row["quantity"],
                    row["option_summary"],
                    row["price"],
                    row["source_note"],
                    row["collected_at"],
                    now,
                    now,
                )
                for row in valid_rows
            ],
        )
        inserted_count = len(valid_rows)

    return {
        "status": "imported" if not errors else "validation_failed",
        "valid_count": len(valid_rows),
        "error_count": len(errors),
        "inserted_count": inserted_count,
        "errors": errors,
    }


def import_cost_profiles(connection: sqlite3.Connection, csv_text: str) -> dict[str, Any]:
    rows, errors = _read_csv_rows(csv_text)
    if rows:
        for column in _missing_columns(rows, COST_PROFILE_COLUMNS):
            errors.append({"row": 1, "field": column, "message": "Required column is missing."})

    product_ids = _product_ids_by_slug(connection)
    valid_rows: list[dict[str, Any]] = []

    if not errors:
        for index, row in enumerate(rows, start=2):
            row_errors = []
            product_slug = row.get("product_slug", "").strip()
            quantity = _positive_int(row.get("quantity", ""))
            unit_cost = _float_value(row.get("unit_cost", ""))
            fixed_cost = _float_value(row.get("fixed_cost", ""))
            minimum_margin_rate = _float_value(row.get("minimum_margin_rate", ""))
            minimum_price = _float_value(row.get("minimum_price", ""))
            option_summary = row.get("option_summary", "").strip()
            product_id = product_ids.get(product_slug)

            if product_id is None:
                row_errors.append({"row": index, "field": "product_slug", "message": "Product must exist before import."})
            if quantity is None:
                row_errors.append({"row": index, "field": "quantity", "message": "Quantity must be positive."})
            if unit_cost is None or unit_cost < 0:
                row_errors.append({"row": index, "field": "unit_cost", "message": "Unit cost must be non-negative."})
            if fixed_cost is None or fixed_cost < 0:
                row_errors.append({"row": index, "field": "fixed_cost", "message": "Fixed cost must be non-negative."})
            if minimum_margin_rate is None or minimum_margin_rate < 0 or minimum_margin_rate >= 1:
                row_errors.append({"row": index, "field": "minimum_margin_rate", "message": "Minimum margin rate must be between 0 and 1."})
            if minimum_price is None or minimum_price < 0:
                row_errors.append({"row": index, "field": "minimum_price", "message": "Minimum price must be non-negative."})
            if not option_summary:
                row_errors.append({"row": index, "field": "option_summary", "message": "Option summary is required."})

            if row_errors:
                errors.extend(row_errors)
                continue

            valid_rows.append(
                {
                    "product_id": product_id,
                    "quantity": quantity,
                    "option_summary": option_summary,
                    "unit_cost": unit_cost,
                    "fixed_cost": fixed_cost,
                    "minimum_margin_rate": minimum_margin_rate,
                    "minimum_price": minimum_price,
                }
            )

    inserted_count = 0
    if not errors:
        now = utc_now()
        connection.executemany(
            """
            INSERT INTO cost_profiles (
                product_id, quantity, option_summary, unit_cost, fixed_cost,
                minimum_margin_rate, minimum_price, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["product_id"],
                    row["quantity"],
                    row["option_summary"],
                    row["unit_cost"],
                    row["fixed_cost"],
                    row["minimum_margin_rate"],
                    row["minimum_price"],
                    now,
                    now,
                )
                for row in valid_rows
            ],
        )
        inserted_count = len(valid_rows)

    return {
        "status": "imported" if not errors else "validation_failed",
        "valid_count": len(valid_rows),
        "error_count": len(errors),
        "inserted_count": inserted_count,
        "errors": errors,
    }


def _write_csv(columns: list[str], rows: list[dict[str, Any]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def export_competitor_prices(connection: sqlite3.Connection) -> str:
    rows = connection.execute(
        """
        SELECT
            c.name AS competitor_name,
            p.slug AS product_slug,
            cp.quantity,
            cp.option_summary,
            cp.price,
            cp.source_note,
            cp.collected_at
        FROM competitor_prices cp
        JOIN competitors c ON c.id = cp.competitor_id
        JOIN products p ON p.id = cp.product_id
        ORDER BY p.slug, cp.quantity, c.name, cp.id
        """
    ).fetchall()
    return _write_csv(COMPETITOR_PRICE_COLUMNS, [dict(row) for row in rows])


def export_cost_profiles(connection: sqlite3.Connection) -> str:
    rows = connection.execute(
        """
        SELECT
            p.slug AS product_slug,
            cp.quantity,
            cp.option_summary,
            cp.unit_cost,
            cp.fixed_cost,
            cp.minimum_margin_rate,
            cp.minimum_price
        FROM cost_profiles cp
        JOIN products p ON p.id = cp.product_id
        ORDER BY p.slug, cp.quantity, cp.id
        """
    ).fetchall()
    return _write_csv(COST_PROFILE_COLUMNS, [dict(row) for row in rows])


def export_price_table_items(connection: sqlite3.Connection, price_table_id: int) -> str | None:
    table = connection.execute("SELECT id FROM price_tables WHERE id = ?", (price_table_id,)).fetchone()
    if table is None:
        return None
    rows = connection.execute(
        """
        SELECT price_table_id, quantity, option_summary, final_price, margin_rate
        FROM price_table_items
        WHERE price_table_id = ?
        ORDER BY quantity, id
        """,
        (price_table_id,),
    ).fetchall()
    return _write_csv(PRICE_TABLE_ITEM_COLUMNS, [dict(row) for row in rows])


def export_candidate_table_items(connection: sqlite3.Connection, candidate_table_id: int) -> str | None:
    table = connection.execute("SELECT id FROM candidate_tables WHERE id = ?", (candidate_table_id,)).fetchone()
    if table is None:
        return None
    rows = connection.execute(
        """
        SELECT
            candidate_table_id,
            quantity,
            candidate_price,
            unit_price,
            cost_floor_price,
            estimated_margin_rate,
            market_lowest_price,
            market_average_price,
            market_highest_price,
            decision_reason_codes,
            warnings
        FROM candidate_table_items
        WHERE candidate_table_id = ?
        ORDER BY quantity, id
        """,
        (candidate_table_id,),
    ).fetchall()
    normalized_rows = []
    for row in rows:
        data = dict(row)
        for field in ("decision_reason_codes", "warnings"):
            try:
                data[field] = json.dumps(json.loads(data[field] or "[]"), ensure_ascii=False)
            except json.JSONDecodeError:
                data[field] = data[field] or "[]"
        normalized_rows.append(data)
    return _write_csv(CANDIDATE_TABLE_ITEM_COLUMNS, normalized_rows)
