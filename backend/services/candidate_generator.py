from __future__ import annotations

import json
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from statistics import median
from typing import Any

from backend.db import utc_now
from backend.services.agent_logger import log_agent_step
from backend.services.market_reference import (
    MarketReferenceError,
    normalize_option_summary,
    resolve_product,
)
from backend.services.strategy_templates import (
    StrategyTemplateError,
    resolve_strategy_template_for_generation,
)


class CandidateGenerationError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class CandidateGenerationNotFoundError(CandidateGenerationError):
    status_code = 404


STRATEGIES = {
    "margin_protect": {
        "label": "Margin Protect",
        "market_multiplier": Decimal("1.03"),
        "no_market_multiplier": Decimal("1.08"),
    },
    "balanced_market": {
        "label": "Balanced Market",
        "market_multiplier": Decimal("1.00"),
        "no_market_multiplier": Decimal("1.05"),
    },
    "premium_local": {
        "label": "Premium Local",
        "market_multiplier": Decimal("1.08"),
        "no_market_multiplier": Decimal("1.12"),
    },
}

DEFAULT_ROUNDING_UNIT = 100


def _money(value: Decimal | int | float | str) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _round_to_unit(value: Decimal, rounding_unit: int) -> Decimal:
    unit = Decimal(str(rounding_unit))
    return (value / unit).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * unit


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
        WHERE product_id = ?
            AND quantity = ?
            AND LOWER(TRIM(option_summary)) = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (product_id, quantity, option_summary),
    ).fetchone()


def _fetch_competitor_prices(
    connection: sqlite3.Connection,
    product_id: int,
    quantity: int,
    option_summary: str,
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT cp.price, c.competitor_type
        FROM competitor_prices cp
        JOIN competitors c ON c.id = cp.competitor_id
        WHERE cp.product_id = ?
            AND cp.quantity = ?
            AND LOWER(TRIM(cp.option_summary)) = ?
            AND c.is_active = 1
        ORDER BY cp.price ASC, c.name ASC
        """,
        (product_id, quantity, option_summary),
    ).fetchall()


def _market_summary(rows: list[sqlite3.Row]) -> dict[str, Any]:
    prices = [Decimal(str(row["price"])) for row in rows]
    if not prices:
        return {
            "lowest_price": None,
            "highest_price": None,
            "average_price": None,
            "median_price": None,
            "count": 0,
        }

    return {
        "lowest_price": _money(min(prices)),
        "highest_price": _money(max(prices)),
        "average_price": _money(sum(prices) / Decimal(len(prices))),
        "median_price": _money(Decimal(str(median(prices)))),
        "count": len(prices),
    }


def _cost_floor(cost_profile: sqlite3.Row, quantity: int) -> tuple[Decimal, Decimal]:
    margin_rate = Decimal(str(cost_profile["minimum_margin_rate"]))
    if margin_rate >= Decimal("1"):
        raise CandidateGenerationError("minimum_margin_rate must be less than 1.")

    base_cost = Decimal(str(cost_profile["fixed_cost"])) + (
        Decimal(str(cost_profile["unit_cost"])) * Decimal(quantity)
    )
    minimum_price_from_margin = base_cost / (Decimal("1") - margin_rate)
    floor = max(minimum_price_from_margin, Decimal(str(cost_profile["minimum_price"])))
    return base_cost, floor


def _build_candidate_item(
    *,
    quantity: int,
    option_summary: str,
    strategy_name: str | None,
    cost_profile: sqlite3.Row,
    market_rows: list[sqlite3.Row],
    rounding_unit: int,
) -> dict[str, Any]:
    base_cost, cost_floor = _cost_floor(cost_profile, quantity)
    summary = _market_summary(market_rows)
    strategy = STRATEGIES[strategy_name]
    warnings: list[str] = []
    reason_codes = ["COST_FLOOR_PROTECTED", f"STRATEGY_{strategy_name.upper()}"]

    if summary["count"] > 0:
        market_average = Decimal(str(summary["average_price"]))
        strategy_target = market_average * strategy["market_multiplier"]
        raw_candidate = max(cost_floor, strategy_target)
        reason_codes.append("MARKET_REFERENCE_USED")
        if any(row["competitor_type"] == "large_online" for row in market_rows):
            reason_codes.append("LARGE_ONLINE_NOT_BLINDLY_FOLLOWED")
        if cost_floor > market_average:
            warnings.append(
                "Cost floor is above the market average, so margin protection controlled the candidate price."
            )
    else:
        raw_candidate = cost_floor * strategy["no_market_multiplier"]
        reason_codes.append("NO_MARKET_REFERENCE")
        warnings.append(
            "No matching competitor reference was found; deterministic cost-floor fallback was used."
        )

    rounded_candidate = _round_to_unit(raw_candidate, rounding_unit)
    rounded_floor = _round_to_unit(cost_floor, rounding_unit)
    candidate_price = max(rounded_candidate, rounded_floor)
    unit_price = candidate_price / Decimal(quantity)
    estimated_margin_rate = (
        (candidate_price - base_cost) / candidate_price
        if candidate_price > Decimal("0")
        else Decimal("0")
    )

    return {
        "quantity": quantity,
        "option_summary": option_summary,
        "candidate_price": _money(candidate_price),
        "unit_price": _money(unit_price),
        "cost_floor_price": _money(cost_floor),
        "estimated_margin_rate": _money(estimated_margin_rate),
        "market_lowest_price": summary["lowest_price"],
        "market_average_price": summary["average_price"],
        "market_median_price": summary["median_price"],
        "market_highest_price": summary["highest_price"],
        "market_summary": summary,
        "decision_reason_codes": reason_codes,
        "warnings": warnings,
    }


def generate_candidate_prices(
    connection: sqlite3.Connection,
    *,
    option_summary: str,
    quantities: list[int],
    strategy_name: str,
    product_id: int | None = None,
    product_slug: str | None = None,
    strategy_template_id: int | None = None,
) -> dict[str, Any]:
    strategy_template = None
    rounding_unit = DEFAULT_ROUNDING_UNIT
    if strategy_template_id is not None:
        try:
            strategy_template = resolve_strategy_template_for_generation(
                connection,
                template_id=strategy_template_id,
            )
        except StrategyTemplateError as exc:
            error_cls = (
                CandidateGenerationNotFoundError
                if getattr(exc, "status_code", 400) == 404
                else CandidateGenerationError
            )
            raise error_cls(exc.detail) from exc
        strategy_name = strategy_template["strategy_name"]
        rounding_unit = strategy_template["rounding_unit"]

    if strategy_name not in STRATEGIES:
        raise CandidateGenerationError(
            "strategy_name must be one of: margin_protect, balanced_market, premium_local."
        )

    unique_quantities = sorted({quantity for quantity in quantities if quantity > 0})
    if len(unique_quantities) != len(quantities):
        raise CandidateGenerationError("Quantities must be positive and unique.")

    normalized_option_summary = normalize_option_summary(option_summary)
    if not normalized_option_summary:
        raise CandidateGenerationError("option_summary is required.")

    try:
        product = resolve_product(connection, product_id, product_slug)
    except MarketReferenceError as exc:
        error_cls = (
            CandidateGenerationNotFoundError
            if getattr(exc, "status_code", 400) == 404
            else CandidateGenerationError
        )
        raise error_cls(exc.detail) from exc

    items = []
    total_market_references = 0
    for quantity in unique_quantities:
        cost_profile = _find_cost_profile(
            connection,
            product["id"],
            quantity,
            normalized_option_summary,
        )
        if cost_profile is None:
            raise CandidateGenerationNotFoundError(
                f"No cost profile matched quantity {quantity}; candidate generation cannot invent prices."
            )

        market_rows = _fetch_competitor_prices(
            connection,
            product["id"],
            quantity,
            normalized_option_summary,
        )
        total_market_references += len(market_rows)
        items.append(
            _build_candidate_item(
                quantity=quantity,
                option_summary=option_summary,
                strategy_name=strategy_name,
                cost_profile=cost_profile,
                market_rows=market_rows,
                rounding_unit=rounding_unit,
            )
        )

    now = utc_now()
    session_cursor = connection.execute(
        """
        INSERT INTO pricing_sessions (
            product_id, option_summary, strategy_name, status, created_at, updated_at
        )
        VALUES (?, ?, ?, 'generated', ?, ?)
        """,
        (product["id"], option_summary, strategy_name, now, now),
    )
    pricing_session_id = session_cursor.lastrowid
    log_agent_step(
        connection,
        pricing_session_id=pricing_session_id,
        step_type="data_loaded",
        title="Product and option loaded",
        message=f"Loaded {product['name']} with option summary: {option_summary}.",
        metadata={
            "product_id": product["id"],
            "option_summary": option_summary,
            "quantities": unique_quantities,
        },
    )
    log_agent_step(
        connection,
        pricing_session_id=pricing_session_id,
        step_type="cost_floor_calculated",
        title="Cost profiles checked",
        message=f"Checked matching cost profiles for {len(unique_quantities)} quantity rows.",
        metadata={"quantity_count": len(unique_quantities)},
    )
    log_agent_step(
        connection,
        pricing_session_id=pricing_session_id,
        step_type="market_reference_analyzed",
        title="Market references analyzed",
        message=f"Found {total_market_references} manually entered competitor reference rows.",
        status="completed" if total_market_references else "warning",
        metadata={"market_reference_count": total_market_references},
    )
    table_name = f"{STRATEGIES[strategy_name]['label']} candidate - {product['name']}"
    table_cursor = connection.execute(
        """
        INSERT INTO candidate_tables (
            pricing_session_id, product_id, name, strategy_name, status, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, 'generated', ?, ?)
        """,
        (pricing_session_id, product["id"], table_name, strategy_name, now, now),
    )
    candidate_table_id = table_cursor.lastrowid
    log_agent_step(
        connection,
        pricing_session_id=pricing_session_id,
        candidate_table_id=candidate_table_id,
        step_type="strategy_applied",
        title="Strategy applied",
        message=f"Applied {strategy_name} using deterministic backend formulas.",
        metadata={"strategy_name": strategy_name},
    )

    for item in items:
        market_summary = item["market_summary"]
        connection.execute(
            """
            INSERT INTO candidate_table_items (
                candidate_table_id, quantity, option_summary, candidate_price, unit_price,
                cost_floor_price, estimated_margin_rate, market_lowest_price,
                market_average_price, market_median_price, market_highest_price,
                market_reference_count, decision_reason_codes, warnings, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                candidate_table_id,
                item["quantity"],
                item["option_summary"],
                item["candidate_price"],
                item["unit_price"],
                item["cost_floor_price"],
                item["estimated_margin_rate"],
                market_summary["lowest_price"],
                market_summary["average_price"],
                market_summary["median_price"],
                market_summary["highest_price"],
                market_summary["count"],
                json.dumps(item["decision_reason_codes"]),
                json.dumps(item["warnings"]),
                now,
                now,
            ),
        )

    log_agent_step(
        connection,
        pricing_session_id=pricing_session_id,
        candidate_table_id=candidate_table_id,
        step_type="candidate_generated",
        title="Candidate table generated",
        message=f"Generated {len(items)} candidate price rows. The table is not active.",
        metadata={"item_count": len(items), "status": "generated"},
    )

    response_warnings = [
        "Generated candidate tables are not active internal price tables and require later admin review.",
        "Competitor prices are manually entered reference data only.",
    ]
    candidate_prices = [Decimal(str(item["candidate_price"])) for item in items]
    summary = {
        "lowest_candidate_price": _money(min(candidate_prices)) if candidate_prices else None,
        "highest_candidate_price": _money(max(candidate_prices)) if candidate_prices else None,
        "average_candidate_price": (
            _money(sum(candidate_prices) / Decimal(len(candidate_prices)))
            if candidate_prices
            else None
        ),
        "total_market_references": sum(
            item["market_summary"]["count"] for item in items
        ),
        "item_count": len(items),
    }

    return {
        "pricing_session_id": pricing_session_id,
        "candidate_table_id": candidate_table_id,
        "candidate_table_name": table_name,
        "product_id": product["id"],
        "product_name": product["name"],
        "option_summary": option_summary,
        "strategy_name": strategy_name,
        "status": "generated",
        "rounding_rule": f"nearest_{rounding_unit}_won",
        "strategy_template": (
            {
                "id": strategy_template["id"],
                "name": strategy_template["name"],
                "slug": strategy_template["slug"],
                "strategy_name": strategy_template["strategy_name"],
                "market_position": strategy_template["market_position"],
                "margin_bias": strategy_template["margin_bias"],
                "competitor_weight_mode": strategy_template["competitor_weight_mode"],
                "rounding_unit": strategy_template["rounding_unit"],
            }
            if strategy_template
            else None
        ),
        "items": items,
        "summary": summary,
        "warnings": response_warnings,
    }
