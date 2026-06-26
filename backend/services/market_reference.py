from __future__ import annotations

import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from typing import Any


class MarketReferenceError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class MarketReferenceNotFoundError(MarketReferenceError):
    status_code = 404


def normalize_option_summary(option_summary: str) -> str:
    return " ".join(option_summary.strip().lower().split())


def money(value: Decimal | int | float | str) -> float:
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return float(amount)


def resolve_product(
    connection: sqlite3.Connection,
    product_id: int | None,
    product_slug: str | None,
) -> sqlite3.Row:
    if product_id is None and not product_slug:
        raise MarketReferenceError("Either product_id or product_slug is required.")

    if product_id is not None:
        product = connection.execute(
            "SELECT id, name, slug FROM products WHERE id = ? AND is_active = 1",
            (product_id,),
        ).fetchone()
    else:
        product = connection.execute(
            "SELECT id, name, slug FROM products WHERE slug = ? AND is_active = 1",
            (product_slug,),
        ).fetchone()

    if product is None:
        raise MarketReferenceNotFoundError("Active product not found.")

    return product


def build_market_reference(
    connection: sqlite3.Connection,
    *,
    quantity: int,
    option_summary: str,
    product_id: int | None = None,
    product_slug: str | None = None,
) -> dict[str, Any]:
    if quantity <= 0:
        raise MarketReferenceError("Quantity must be greater than zero.")

    normalized_option_summary = normalize_option_summary(option_summary)
    if not normalized_option_summary:
        raise MarketReferenceError("option_summary is required.")

    product = resolve_product(connection, product_id, product_slug)

    rows = connection.execute(
        """
        SELECT
            c.name AS competitor_name,
            c.competitor_type,
            cp.price,
            cp.source_note,
            cp.collected_at
        FROM competitor_prices cp
        JOIN competitors c ON c.id = cp.competitor_id
        WHERE
            cp.product_id = ?
            AND cp.quantity = ?
            AND LOWER(TRIM(cp.option_summary)) = ?
            AND c.is_active = 1
        ORDER BY cp.price ASC, c.name ASC
        """,
        (product["id"], quantity, normalized_option_summary),
    ).fetchall()

    prices = [Decimal(str(row["price"])) for row in rows]
    summary = {
        "lowest_price": money(min(prices)) if prices else None,
        "highest_price": money(max(prices)) if prices else None,
        "average_price": money(sum(prices) / Decimal(len(prices))) if prices else None,
        "count": len(prices),
    }

    return {
        "product_id": product["id"],
        "product_name": product["name"],
        "quantity": quantity,
        "option_summary": option_summary,
        "competitor_prices": [
            {
                "competitor_name": row["competitor_name"],
                "competitor_type": row["competitor_type"],
                "price": money(row["price"]),
                "source_note": row["source_note"],
                "collected_at": row["collected_at"],
            }
            for row in rows
        ],
        "summary": summary,
    }
