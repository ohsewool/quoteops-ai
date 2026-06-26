from __future__ import annotations

import sqlite3
from typing import Any

from backend.db import rows_to_dicts, utc_now


class StrategyTemplateError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class StrategyTemplateNotFoundError(StrategyTemplateError):
    status_code = 404


STRATEGY_NAMES = {"margin_protect", "balanced_market", "premium_local"}
MARKET_POSITIONS = {"conservative", "balanced", "premium"}
MARGIN_BIASES = {"low", "medium", "high"}
COMPETITOR_WEIGHT_MODES = {
    "ignore_large_online_lowest",
    "balanced_reference",
    "premium_reference",
}
ROUNDING_UNITS = {100, 500, 1000}


def _bool(value: Any) -> bool:
    return bool(value)


def _serialize(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    data["is_default"] = _bool(data["is_default"])
    data["is_active"] = _bool(data["is_active"])
    return data


def _validate_template_values(values: dict[str, Any]) -> None:
    if "strategy_name" in values and values["strategy_name"] not in STRATEGY_NAMES:
        raise StrategyTemplateError(
            "strategy_name must be one of: margin_protect, balanced_market, premium_local."
        )
    if "market_position" in values and values["market_position"] not in MARKET_POSITIONS:
        raise StrategyTemplateError("market_position must be one of: conservative, balanced, premium.")
    if "margin_bias" in values and values["margin_bias"] not in MARGIN_BIASES:
        raise StrategyTemplateError("margin_bias must be one of: low, medium, high.")
    if (
        "competitor_weight_mode" in values
        and values["competitor_weight_mode"] not in COMPETITOR_WEIGHT_MODES
    ):
        raise StrategyTemplateError(
            "competitor_weight_mode must be one of: ignore_large_online_lowest, balanced_reference, premium_reference."
        )
    if "rounding_unit" in values and values["rounding_unit"] not in ROUNDING_UNITS:
        raise StrategyTemplateError("rounding_unit must be one of: 100, 500, 1000.")


def _ensure_exists(
    connection: sqlite3.Connection,
    table: str,
    row_id: int,
    label: str,
) -> None:
    row = connection.execute(f"SELECT id FROM {table} WHERE id = ?", (row_id,)).fetchone()
    if row is None:
        raise StrategyTemplateError(f"{label} not found.")


def _fetch_template_row(connection: sqlite3.Connection, template_id: int) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT
            st.id, st.name, st.slug, st.description, st.product_id,
            p.name AS product_name, st.product_category_id,
            pc.name AS product_category_name, st.strategy_name,
            st.market_position, st.margin_bias, st.competitor_weight_mode,
            st.rounding_unit, st.is_default, st.is_active,
            st.created_at, st.updated_at
        FROM strategy_templates st
        LEFT JOIN products p ON p.id = st.product_id
        LEFT JOIN product_categories pc ON pc.id = st.product_category_id
        WHERE st.id = ?
        """,
        (template_id,),
    ).fetchone()


def get_strategy_template(connection: sqlite3.Connection, template_id: int) -> dict[str, Any]:
    row = _fetch_template_row(connection, template_id)
    if row is None:
        raise StrategyTemplateNotFoundError("Strategy template not found.")
    return _serialize(row)


def list_strategy_templates(
    connection: sqlite3.Connection,
    *,
    product_id: int | None = None,
    product_category_id: int | None = None,
    is_active: bool | None = None,
) -> list[dict[str, Any]]:
    where = []
    values: list[Any] = []
    if product_id is not None:
        where.append("(st.product_id = ? OR st.product_id IS NULL)")
        values.append(product_id)
    if product_category_id is not None:
        where.append("(st.product_category_id = ? OR st.product_category_id IS NULL)")
        values.append(product_category_id)
    if is_active is not None:
        where.append("st.is_active = ?")
        values.append(1 if is_active else 0)
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    rows = connection.execute(
        f"""
        SELECT
            st.id, st.name, st.slug, st.description, st.product_id,
            p.name AS product_name, st.product_category_id,
            pc.name AS product_category_name, st.strategy_name,
            st.market_position, st.margin_bias, st.competitor_weight_mode,
            st.rounding_unit, st.is_default, st.is_active,
            st.created_at, st.updated_at
        FROM strategy_templates st
        LEFT JOIN products p ON p.id = st.product_id
        LEFT JOIN product_categories pc ON pc.id = st.product_category_id
        {where_clause}
        ORDER BY st.is_default DESC, st.product_id IS NULL ASC, st.id ASC
        """,
        values,
    ).fetchall()
    return [_serialize(row) for row in rows]


def list_product_strategy_templates(
    connection: sqlite3.Connection,
    *,
    product_id: int,
) -> list[dict[str, Any]]:
    product = connection.execute(
        "SELECT id, category_id FROM products WHERE id = ?",
        (product_id,),
    ).fetchone()
    if product is None:
        raise StrategyTemplateNotFoundError("Product not found.")
    return list_strategy_templates(
        connection,
        product_id=product_id,
        product_category_id=product["category_id"],
        is_active=True,
    )


def create_strategy_template(
    connection: sqlite3.Connection,
    values: dict[str, Any],
) -> dict[str, Any]:
    _validate_template_values(values)
    if values.get("product_id") is not None:
        _ensure_exists(connection, "products", values["product_id"], "Product")
    if values.get("product_category_id") is not None:
        _ensure_exists(
            connection,
            "product_categories",
            values["product_category_id"],
            "Product category",
        )
    now = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO strategy_templates (
            name, slug, description, product_id, product_category_id,
            strategy_name, market_position, margin_bias, competitor_weight_mode,
            rounding_unit, is_default, is_active, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            values["name"],
            values["slug"],
            values.get("description", ""),
            values.get("product_id"),
            values.get("product_category_id"),
            values["strategy_name"],
            values.get("market_position", "balanced"),
            values.get("margin_bias", "medium"),
            values.get("competitor_weight_mode", "balanced_reference"),
            values.get("rounding_unit", 100),
            1 if values.get("is_default") else 0,
            1 if values.get("is_active", True) else 0,
            now,
            now,
        ),
    )
    return get_strategy_template(connection, cursor.lastrowid)


def update_strategy_template(
    connection: sqlite3.Connection,
    template_id: int,
    updates: dict[str, Any],
) -> dict[str, Any]:
    if not updates:
        raise StrategyTemplateError("No strategy template fields to update.")
    get_strategy_template(connection, template_id)
    _validate_template_values(updates)
    if updates.get("product_id") is not None:
        _ensure_exists(connection, "products", updates["product_id"], "Product")
    if updates.get("product_category_id") is not None:
        _ensure_exists(
            connection,
            "product_categories",
            updates["product_category_id"],
            "Product category",
        )

    allowed = [
        "name",
        "slug",
        "description",
        "product_id",
        "product_category_id",
        "strategy_name",
        "market_position",
        "margin_bias",
        "competitor_weight_mode",
        "rounding_unit",
        "is_default",
        "is_active",
    ]
    assignments = []
    values = []
    for field in allowed:
        if field in updates:
            assignments.append(f"{field} = ?")
            value = updates[field]
            if field in {"is_default", "is_active"} and value is not None:
                value = 1 if value else 0
            values.append(value)
    assignments.append("updated_at = ?")
    values.append(utc_now())
    values.append(template_id)
    connection.execute(
        f"UPDATE strategy_templates SET {', '.join(assignments)} WHERE id = ?",
        values,
    )
    return get_strategy_template(connection, template_id)


def archive_strategy_template(
    connection: sqlite3.Connection,
    template_id: int,
) -> dict[str, Any]:
    get_strategy_template(connection, template_id)
    connection.execute(
        """
        UPDATE strategy_templates
        SET is_active = 0, updated_at = ?
        WHERE id = ?
        """,
        (utc_now(), template_id),
    )
    return get_strategy_template(connection, template_id)


def resolve_strategy_template_for_generation(
    connection: sqlite3.Connection,
    *,
    template_id: int,
) -> dict[str, Any]:
    template = get_strategy_template(connection, template_id)
    if not template["is_active"]:
        raise StrategyTemplateError("Strategy template is inactive.")
    return template
