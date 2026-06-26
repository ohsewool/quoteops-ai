from __future__ import annotations

import sqlite3
from statistics import mean
from typing import Any


MARKET_ABOVE_AVERAGE_WARNING_RATE = 0.20
MARKET_BELOW_AVERAGE_WARNING_RATE = 0.15


class PricingSimulationError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _resolve_product(
    connection: sqlite3.Connection,
    product_id: int | None,
    product_slug: str | None,
) -> sqlite3.Row:
    if product_id is not None:
        row = connection.execute(
            "SELECT id, name FROM products WHERE id = ?",
            (product_id,),
        ).fetchone()
    else:
        row = connection.execute(
            "SELECT id, name FROM products WHERE slug = ?",
            (product_slug,),
        ).fetchone()
    if row is None:
        raise PricingSimulationError(404, "Product not found.")
    return row


def _resolve_candidate_table(
    connection: sqlite3.Connection,
    candidate_table_id: int,
    product_id: int,
) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT id, product_id, status
        FROM candidate_tables
        WHERE id = ?
        """,
        (candidate_table_id,),
    ).fetchone()
    if row is None:
        raise PricingSimulationError(404, "Candidate table not found.")
    if row["product_id"] != product_id:
        raise PricingSimulationError(400, "Candidate table does not belong to the selected product.")
    return row


def _resolve_baseline_table(
    connection: sqlite3.Connection,
    product_id: int,
    baseline_price_table_id: int | None,
) -> sqlite3.Row | None:
    if baseline_price_table_id is not None:
        row = connection.execute(
            """
            SELECT id, product_id, status
            FROM price_tables
            WHERE id = ?
            """,
            (baseline_price_table_id,),
        ).fetchone()
        if row is None:
            raise PricingSimulationError(404, "Baseline price table not found.")
        if row["product_id"] != product_id:
            raise PricingSimulationError(400, "Baseline price table does not belong to the selected product.")
        return row

    return connection.execute(
        """
        SELECT id, product_id, status
        FROM price_tables
        WHERE product_id = ? AND status = 'active'
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """,
        (product_id,),
    ).fetchone()


def _load_candidate_items(
    connection: sqlite3.Connection,
    candidate_table_id: int,
    option_summary: str | None,
) -> list[sqlite3.Row]:
    filters = ["candidate_table_id = ?"]
    values: list[Any] = [candidate_table_id]
    if option_summary:
        filters.append("LOWER(TRIM(option_summary)) = ?")
        values.append(_normalize(option_summary))

    rows = connection.execute(
        f"""
        SELECT
            quantity, option_summary, candidate_price
        FROM candidate_table_items
        WHERE {" AND ".join(filters)}
        ORDER BY quantity, id
        """,
        values,
    ).fetchall()
    if not rows:
        raise PricingSimulationError(404, "No candidate table items matched this simulation request.")
    return rows


def _baseline_price(
    connection: sqlite3.Connection,
    baseline_price_table_id: int | None,
    quantity: int,
    option_summary: str,
) -> float | None:
    if baseline_price_table_id is None:
        return None
    row = connection.execute(
        """
        SELECT final_price
        FROM price_table_items
        WHERE price_table_id = ?
          AND quantity = ?
          AND LOWER(TRIM(option_summary)) = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (baseline_price_table_id, quantity, _normalize(option_summary)),
    ).fetchone()
    return float(row["final_price"]) if row else None


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


def _market_summary(
    connection: sqlite3.Connection,
    product_id: int,
    quantity: int,
    option_summary: str,
) -> dict[str, float | None]:
    rows = connection.execute(
        """
        SELECT price
        FROM competitor_prices
        WHERE product_id = ?
          AND quantity = ?
          AND LOWER(TRIM(option_summary)) = ?
        """,
        (product_id, quantity, _normalize(option_summary)),
    ).fetchall()
    prices = [float(row["price"]) for row in rows]
    if not prices:
        return {"lowest": None, "average": None, "highest": None}
    return {
        "lowest": min(prices),
        "average": mean(prices),
        "highest": max(prices),
    }


def _margin_rate(price: float | None, base_cost: float | None) -> float | None:
    if price is None or base_cost is None or price == 0:
        return None
    return (price - base_cost) / price


def _rate_delta(value: float | None, baseline: float | None) -> float | None:
    if value is None or baseline in (None, 0):
        return None
    return (value - baseline) / baseline


def simulate_pricing(
    connection: sqlite3.Connection,
    *,
    product_id: int | None,
    product_slug: str | None,
    candidate_table_id: int,
    baseline_price_table_id: int | None,
    option_summary: str | None,
    volume_assumptions: list[dict[str, int]] | None,
) -> dict[str, Any]:
    product = _resolve_product(connection, product_id, product_slug)
    resolved_product_id = int(product["id"])
    _resolve_candidate_table(connection, candidate_table_id, resolved_product_id)
    baseline_table = _resolve_baseline_table(connection, resolved_product_id, baseline_price_table_id)
    resolved_baseline_id = int(baseline_table["id"]) if baseline_table else None
    candidate_items = _load_candidate_items(connection, candidate_table_id, option_summary)
    volume_by_quantity = {
        item["quantity"]: item["expected_order_count"]
        for item in (volume_assumptions or [])
    }

    items = []
    baseline_total_revenue = 0.0
    candidate_total_revenue = 0.0
    baseline_total_gross_profit = 0.0
    candidate_total_gross_profit = 0.0
    margin_deltas = []
    top_level_warnings: set[str] = set()

    if resolved_baseline_id is None:
        top_level_warnings.add("MISSING_BASELINE_PRICE")

    for candidate_item in candidate_items:
        quantity = int(candidate_item["quantity"])
        item_option_summary = candidate_item["option_summary"]
        expected_order_count = int(volume_by_quantity.get(quantity, 1))
        candidate_price = float(candidate_item["candidate_price"])
        baseline_price = _baseline_price(
            connection,
            resolved_baseline_id,
            quantity,
            item_option_summary,
        )

        cost_profile = _cost_profile(connection, resolved_product_id, quantity, item_option_summary)
        base_cost = None
        if cost_profile is not None:
            base_cost = float(cost_profile["fixed_cost"]) + (float(cost_profile["unit_cost"]) * quantity)

        market = _market_summary(connection, resolved_product_id, quantity, item_option_summary)
        market_average = market["average"]

        baseline_margin_rate = _margin_rate(baseline_price, base_cost)
        candidate_margin_rate = _margin_rate(candidate_price, base_cost)
        margin_delta = (
            candidate_margin_rate - baseline_margin_rate
            if candidate_margin_rate is not None and baseline_margin_rate is not None
            else None
        )
        baseline_revenue = baseline_price * expected_order_count if baseline_price is not None else None
        candidate_revenue = candidate_price * expected_order_count
        baseline_gross_profit = (
            (baseline_price - base_cost) * expected_order_count
            if baseline_price is not None and base_cost is not None
            else None
        )
        candidate_gross_profit = (
            (candidate_price - base_cost) * expected_order_count
            if base_cost is not None
            else None
        )

        warnings = []
        if baseline_price is None:
            warnings.append("MISSING_BASELINE_PRICE")
        if base_cost is None:
            warnings.append("MISSING_COST_PROFILE")
        elif candidate_price < base_cost:
            warnings.append("CANDIDATE_PRICE_BELOW_COST")
        if margin_delta is not None and margin_delta < 0:
            warnings.append("CANDIDATE_MARGIN_LOWER_THAN_BASELINE")
        if market_average is None:
            warnings.append("MISSING_MARKET_DATA")
        else:
            market_position_rate = (candidate_price - market_average) / market_average
            if market_position_rate > MARKET_ABOVE_AVERAGE_WARNING_RATE:
                warnings.append("CANDIDATE_PRICE_MUCH_ABOVE_MARKET_AVERAGE")
            if market_position_rate < -MARKET_BELOW_AVERAGE_WARNING_RATE:
                warnings.append("CANDIDATE_PRICE_MUCH_BELOW_MARKET_AVERAGE")

        top_level_warnings.update(warnings)
        if margin_delta is not None:
            margin_deltas.append(margin_delta)
        if baseline_revenue is not None:
            baseline_total_revenue += baseline_revenue
        candidate_total_revenue += candidate_revenue
        if baseline_gross_profit is not None:
            baseline_total_gross_profit += baseline_gross_profit
        if candidate_gross_profit is not None:
            candidate_total_gross_profit += candidate_gross_profit

        items.append(
            {
                "quantity": quantity,
                "option_summary": item_option_summary,
                "expected_order_count": expected_order_count,
                "baseline_price": baseline_price,
                "candidate_price": candidate_price,
                "price_delta": candidate_price - baseline_price if baseline_price is not None else None,
                "price_delta_rate": _rate_delta(candidate_price, baseline_price),
                "base_cost": base_cost,
                "baseline_margin_rate": baseline_margin_rate,
                "candidate_margin_rate": candidate_margin_rate,
                "margin_delta": margin_delta,
                "baseline_revenue": baseline_revenue,
                "candidate_revenue": candidate_revenue,
                "revenue_delta": candidate_revenue - baseline_revenue if baseline_revenue is not None else None,
                "baseline_gross_profit": baseline_gross_profit,
                "candidate_gross_profit": candidate_gross_profit,
                "gross_profit_delta": (
                    candidate_gross_profit - baseline_gross_profit
                    if candidate_gross_profit is not None and baseline_gross_profit is not None
                    else None
                ),
                "market_lowest_price": market["lowest"],
                "market_average_price": market_average,
                "market_highest_price": market["highest"],
                "candidate_vs_market_average_rate": _rate_delta(candidate_price, market_average),
                "warnings": warnings,
            }
        )

    return {
        "product_id": resolved_product_id,
        "product_name": product["name"],
        "candidate_table_id": candidate_table_id,
        "baseline_price_table_id": resolved_baseline_id,
        "summary": {
            "item_count": len(items),
            "baseline_total_revenue": baseline_total_revenue,
            "candidate_total_revenue": candidate_total_revenue,
            "revenue_delta": candidate_total_revenue - baseline_total_revenue,
            "baseline_total_gross_profit": baseline_total_gross_profit,
            "candidate_total_gross_profit": candidate_total_gross_profit,
            "gross_profit_delta": candidate_total_gross_profit - baseline_total_gross_profit,
            "average_margin_delta": mean(margin_deltas) if margin_deltas else None,
            "warning_count": sum(len(item["warnings"]) for item in items),
        },
        "items": items,
        "warnings": sorted(top_level_warnings),
    }
