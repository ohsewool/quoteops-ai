from __future__ import annotations

import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


class QuoteCalculationError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class ProductNotFoundError(QuoteCalculationError):
    status_code = 404


class QuoteDataNotFoundError(QuoteCalculationError):
    status_code = 404


def _normalize_option_summary(option_summary: str) -> str:
    return " ".join(option_summary.strip().lower().split())


def _money(value: Decimal | int | float | str) -> float:
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(amount)


def _resolve_product(
    connection: sqlite3.Connection,
    product_id: int | None,
    product_slug: str | None,
) -> sqlite3.Row:
    if product_id is None and not product_slug:
        raise QuoteCalculationError("Either product_id or product_slug is required.")

    if product_id is not None:
        product = connection.execute(
            """
            SELECT id, name, slug
            FROM products
            WHERE id = ? AND is_active = 1
            """,
            (product_id,),
        ).fetchone()
    else:
        product = connection.execute(
            """
            SELECT id, name, slug
            FROM products
            WHERE slug = ? AND is_active = 1
            """,
            (product_slug,),
        ).fetchone()

    if product is None:
        raise ProductNotFoundError("Active product not found.")

    return product


def _find_active_price_table_item(
    connection: sqlite3.Connection,
    product_id: int,
    quantity: int,
    option_summary: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT
            pt.name AS price_table_name,
            pti.final_price AS final_price
        FROM price_tables pt
        JOIN price_table_items pti ON pti.price_table_id = pt.id
        WHERE
            pt.product_id = ?
            AND pt.status = 'active'
            AND pti.quantity = ?
            AND LOWER(TRIM(pti.option_summary)) = ?
        ORDER BY pt.id DESC, pti.id DESC
        LIMIT 1
        """,
        (product_id, quantity, option_summary),
    ).fetchone()


def _find_cost_profile(
    connection: sqlite3.Connection,
    product_id: int,
    quantity: int,
    option_summary: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT unit_cost, fixed_cost, minimum_margin_rate, minimum_price
        FROM cost_profiles
        WHERE
            product_id = ?
            AND quantity = ?
            AND LOWER(TRIM(option_summary)) = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (product_id, quantity, option_summary),
    ).fetchone()


def calculate_quote(
    connection: sqlite3.Connection,
    *,
    quantity: int,
    option_summary: str,
    product_id: int | None = None,
    product_slug: str | None = None,
) -> dict[str, Any]:
    if quantity <= 0:
        raise QuoteCalculationError("Quantity must be greater than zero.")

    normalized_option_summary = _normalize_option_summary(option_summary)
    if not normalized_option_summary:
        raise QuoteCalculationError("option_summary is required.")

    product = _resolve_product(connection, product_id, product_slug)

    active_item = _find_active_price_table_item(
        connection,
        product["id"],
        quantity,
        normalized_option_summary,
    )
    if active_item is not None:
        quote_price = _money(active_item["final_price"])
        return {
            "product_id": product["id"],
            "product_name": product["name"],
            "quantity": quantity,
            "option_summary": option_summary,
            "quote_price": quote_price,
            "unit_price": _money(Decimal(str(quote_price)) / Decimal(quantity)),
            "calculation_source": "active_price_table",
            "price_table_name": active_item["price_table_name"],
            "warnings": [],
        }

    cost_profile = _find_cost_profile(
        connection,
        product["id"],
        quantity,
        normalized_option_summary,
    )
    if cost_profile is None:
        raise QuoteDataNotFoundError(
            "No active price table row or cost profile matched this product, quantity, and option_summary."
        )

    margin_rate = Decimal(str(cost_profile["minimum_margin_rate"]))
    if margin_rate >= Decimal("1"):
        raise QuoteCalculationError("minimum_margin_rate must be less than 1.")

    base_cost = Decimal(str(cost_profile["fixed_cost"])) + (
        Decimal(str(cost_profile["unit_cost"])) * Decimal(quantity)
    )
    minimum_price_from_margin = base_cost / (Decimal("1") - margin_rate)
    quote_price = max(minimum_price_from_margin, Decimal(str(cost_profile["minimum_price"])))
    quote_price = Decimal(str(_money(quote_price)))

    return {
        "product_id": product["id"],
        "product_name": product["name"],
        "quantity": quantity,
        "option_summary": option_summary,
        "quote_price": _money(quote_price),
        "unit_price": _money(quote_price / Decimal(quantity)),
        "calculation_source": "cost_profile_fallback",
        "price_table_name": None,
        "warnings": [
            "No matching active price table row was found; quote used deterministic cost profile fallback."
        ],
    }
