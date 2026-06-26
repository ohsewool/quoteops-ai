from __future__ import annotations

import sqlite3
from statistics import mean
from typing import Any


PRICE_INCREASE_WARNING_RATE = 0.20
PRICE_DECREASE_WARNING_RATE = 0.15


class PriceTableComparisonError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _round_rate(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def _fetch_price_table(connection: sqlite3.Connection, price_table_id: int) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT pt.id, pt.product_id, pt.name, pt.status, pt.strategy_name,
               pt.created_at, pt.updated_at, p.name AS product_name
        FROM price_tables pt
        JOIN products p ON p.id = pt.product_id
        WHERE pt.id = ?
        """,
        (price_table_id,),
    ).fetchone()
    if row is None:
        raise PriceTableComparisonError(404, "Price table not found.")
    return row


def _resolve_default_baseline(
    connection: sqlite3.Connection,
    comparison_table: sqlite3.Row,
) -> sqlite3.Row | None:
    earlier = connection.execute(
        """
        SELECT id, product_id, status
        FROM price_tables
        WHERE product_id = ?
          AND id != ?
          AND id < ?
          AND status IN ('active', 'archived')
        ORDER BY id DESC
        LIMIT 1
        """,
        (
            comparison_table["product_id"],
            comparison_table["id"],
            comparison_table["id"],
        ),
    ).fetchone()
    if earlier is not None:
        return earlier

    return connection.execute(
        """
        SELECT id, product_id, status
        FROM price_tables
        WHERE product_id = ?
          AND id != ?
          AND status IN ('active', 'archived')
        ORDER BY id DESC
        LIMIT 1
        """,
        (comparison_table["product_id"], comparison_table["id"]),
    ).fetchone()


def _resolve_baseline_table(
    connection: sqlite3.Connection,
    comparison_table: sqlite3.Row,
    baseline_price_table_id: int | None,
) -> sqlite3.Row | None:
    if baseline_price_table_id is None:
        return _resolve_default_baseline(connection, comparison_table)

    baseline = _fetch_price_table(connection, baseline_price_table_id)
    if baseline["product_id"] != comparison_table["product_id"]:
        raise PriceTableComparisonError(
            400,
            "Baseline price table must belong to the same product as the comparison table.",
        )
    return baseline


def _load_price_items(
    connection: sqlite3.Connection,
    price_table_id: int | None,
) -> dict[tuple[int, str], dict[str, Any]]:
    if price_table_id is None:
        return {}
    rows = connection.execute(
        """
        SELECT quantity, option_summary, final_price, margin_rate
        FROM price_table_items
        WHERE price_table_id = ?
        ORDER BY quantity, id
        """,
        (price_table_id,),
    ).fetchall()
    items: dict[tuple[int, str], dict[str, Any]] = {}
    for row in rows:
        key = (int(row["quantity"]), _normalize(row["option_summary"]))
        items[key] = {
            "quantity": int(row["quantity"]),
            "option_summary": row["option_summary"],
            "price": float(row["final_price"]),
            "stored_margin_rate": float(row["margin_rate"]),
        }
    return items


def _cost_profile(
    connection: sqlite3.Connection,
    product_id: int,
    quantity: int,
    option_summary: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT unit_cost, fixed_cost
        FROM cost_profiles
        WHERE product_id = ?
          AND quantity = ?
          AND LOWER(TRIM(option_summary)) = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (product_id, quantity, _normalize(option_summary)),
    ).fetchone()


def _margin_rate(price: float | None, base_cost: float | None) -> float | None:
    if price is None or base_cost is None or price == 0:
        return None
    return (price - base_cost) / price


def _change_type(
    baseline_price: float | None,
    comparison_price: float | None,
) -> str:
    if baseline_price is None and comparison_price is not None:
        return "new_item"
    if baseline_price is not None and comparison_price is None:
        return "removed_item"
    if baseline_price == comparison_price:
        return "unchanged"
    if comparison_price is not None and baseline_price is not None and comparison_price > baseline_price:
        return "increased"
    return "decreased"


def compare_price_tables(
    connection: sqlite3.Connection,
    *,
    comparison_price_table_id: int,
    baseline_price_table_id: int | None,
) -> dict[str, Any]:
    comparison_table = _fetch_price_table(connection, comparison_price_table_id)
    baseline_table = _resolve_baseline_table(connection, comparison_table, baseline_price_table_id)
    resolved_baseline_id = int(baseline_table["id"]) if baseline_table else None

    baseline_items = _load_price_items(connection, resolved_baseline_id)
    comparison_items = _load_price_items(connection, comparison_price_table_id)
    item_keys = sorted(
        set(baseline_items) | set(comparison_items),
        key=lambda key: (key[0], baseline_items.get(key, comparison_items.get(key, {})).get("option_summary", "")),
    )
    if not item_keys:
        raise PriceTableComparisonError(404, "No price table items were found to compare.")

    items = []
    warning_set: set[str] = set()
    delta_rates = []
    total_price_delta = 0.0

    if resolved_baseline_id is None:
        warning_set.add("MISSING_BASELINE_ITEM")

    for key in item_keys:
        baseline_item = baseline_items.get(key)
        comparison_item = comparison_items.get(key)
        quantity = key[0]
        option_summary = (
            comparison_item["option_summary"]
            if comparison_item is not None
            else baseline_item["option_summary"]
        )
        baseline_price = baseline_item["price"] if baseline_item is not None else None
        comparison_price = comparison_item["price"] if comparison_item is not None else None

        price_delta = None
        price_delta_rate = None
        if baseline_price is not None and comparison_price is not None:
            price_delta = comparison_price - baseline_price
            total_price_delta += price_delta
            if baseline_price != 0:
                price_delta_rate = price_delta / baseline_price
                delta_rates.append(price_delta_rate)

        cost_profile = _cost_profile(
            connection,
            int(comparison_table["product_id"]),
            quantity,
            option_summary,
        )
        base_cost = None
        if cost_profile is not None:
            base_cost = float(cost_profile["fixed_cost"]) + (float(cost_profile["unit_cost"]) * quantity)

        baseline_margin_rate = _margin_rate(baseline_price, base_cost)
        comparison_margin_rate = _margin_rate(comparison_price, base_cost)
        margin_delta = (
            comparison_margin_rate - baseline_margin_rate
            if comparison_margin_rate is not None and baseline_margin_rate is not None
            else None
        )

        warnings = []
        if baseline_item is None:
            warnings.append("MISSING_BASELINE_ITEM")
        if comparison_item is None:
            warnings.append("MISSING_COMPARISON_ITEM")
        if cost_profile is None:
            warnings.append("MISSING_COST_PROFILE")
        if price_delta_rate is not None and price_delta_rate > PRICE_INCREASE_WARNING_RATE:
            warnings.append("PRICE_INCREASE_OVER_20_PERCENT")
        if price_delta_rate is not None and price_delta_rate < -PRICE_DECREASE_WARNING_RATE:
            warnings.append("PRICE_DECREASE_OVER_15_PERCENT")
        if margin_delta is not None and margin_delta < 0:
            warnings.append("MARGIN_DECREASED")
        if base_cost is not None and comparison_price is not None and comparison_price < base_cost:
            warnings.append("PRICE_BELOW_COST")

        warning_set.update(warnings)
        change_type = _change_type(baseline_price, comparison_price)
        items.append(
            {
                "quantity": quantity,
                "option_summary": option_summary,
                "baseline_price": baseline_price,
                "comparison_price": comparison_price,
                "price_delta": price_delta,
                "price_delta_rate": _round_rate(price_delta_rate),
                "baseline_margin_rate": _round_rate(baseline_margin_rate),
                "comparison_margin_rate": _round_rate(comparison_margin_rate),
                "margin_delta": _round_rate(margin_delta),
                "change_type": change_type,
                "warnings": warnings,
            }
        )

    changed_count = sum(1 for item in items if item["change_type"] != "unchanged")
    unchanged_count = len(items) - changed_count

    return {
        "product_id": int(comparison_table["product_id"]),
        "product_name": comparison_table["product_name"],
        "baseline_price_table_id": resolved_baseline_id,
        "comparison_price_table_id": comparison_price_table_id,
        "summary": {
            "item_count": len(items),
            "changed_count": changed_count,
            "unchanged_count": unchanged_count,
            "average_price_delta_rate": _round_rate(mean(delta_rates)) if delta_rates else None,
            "total_price_delta": total_price_delta,
            "warning_count": sum(len(item["warnings"]) for item in items),
        },
        "items": items,
        "warnings": sorted(warning_set),
    }


def list_price_table_history(
    connection: sqlite3.Connection,
    *,
    product_id: int | None = None,
) -> list[dict[str, Any]]:
    filters = []
    values: list[Any] = []
    if product_id is not None:
        filters.append("pt.product_id = ?")
        values.append(product_id)

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = connection.execute(
        f"""
        SELECT
            pt.id AS price_table_id,
            pt.product_id,
            p.name AS product_name,
            pt.name,
            pt.status,
            pt.strategy_name,
            pt.created_at,
            pt.updated_at,
            a.id AS approval_id,
            a.action AS approval_action,
            a.status AS approval_status,
            a.reviewer_name,
            a.reviewer_note,
            a.created_at AS approved_at,
            a.candidate_table_id
        FROM price_tables pt
        JOIN products p ON p.id = pt.product_id
        LEFT JOIN approvals a ON a.created_price_table_id = pt.id
        {where_clause}
        ORDER BY pt.product_id, pt.id DESC
        """,
        values,
    ).fetchall()
    return [dict(row) for row in rows]

