from __future__ import annotations

import json
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from backend.db import utc_now
from backend.services.agent_logger import log_agent_step
from backend.services.market_reference import normalize_option_summary


class CandidateValidationError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class CandidateValidationNotFoundError(CandidateValidationError):
    status_code = 404


MARKET_BELOW_AVERAGE_THRESHOLD = Decimal("0.15")
MARKET_ABOVE_AVERAGE_THRESHOLD = Decimal("0.20")
LOWEST_MARKET_PROXIMITY_THRESHOLD = Decimal("0.03")
UNIT_PRICE_INCREASE_THRESHOLD = Decimal("0.05")


def _money(value: Decimal | int | float | str) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _rate(value: Decimal | int | float | str) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))


def _check(code: str, level: str, message: str) -> dict[str, str]:
    return {"code": code, "level": level, "message": message}


def _risk_for_levels(levels: list[str]) -> str:
    if "error" in levels:
        return "high"
    if "warning" in levels:
        return "medium"
    return "low"


def _status_for_levels(levels: list[str]) -> str:
    if "error" in levels:
        return "error"
    if "warning" in levels:
        return "warning"
    return "pass"


def _fetch_candidate_table(
    connection: sqlite3.Connection,
    candidate_table_id: int,
) -> sqlite3.Row:
    table = connection.execute(
        """
        SELECT id, product_id, name, strategy_name, status
        FROM candidate_tables
        WHERE id = ?
        """,
        (candidate_table_id,),
    ).fetchone()
    if table is None:
        raise CandidateValidationNotFoundError("Candidate table not found.")
    return table


def _fetch_candidate_items(
    connection: sqlite3.Connection,
    candidate_table_id: int,
) -> list[sqlite3.Row]:
    rows = connection.execute(
        """
        SELECT
            id, quantity, option_summary, candidate_price, unit_price,
            cost_floor_price, estimated_margin_rate, market_lowest_price,
            market_average_price, market_median_price, market_highest_price,
            market_reference_count
        FROM candidate_table_items
        WHERE candidate_table_id = ?
        ORDER BY quantity ASC, id ASC
        """,
        (candidate_table_id,),
    ).fetchall()
    if not rows:
        raise CandidateValidationNotFoundError("Candidate table has no items to validate.")
    return rows


def _find_cost_profile(
    connection: sqlite3.Connection,
    product_id: int,
    quantity: int,
    option_summary: str,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT minimum_margin_rate
        FROM cost_profiles
        WHERE product_id = ?
            AND quantity = ?
            AND LOWER(TRIM(option_summary)) = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (product_id, quantity, normalize_option_summary(option_summary)),
    ).fetchone()


def _validate_item(
    *,
    item: sqlite3.Row,
    cost_profile: sqlite3.Row | None,
) -> dict[str, Any]:
    candidate_price = Decimal(str(item["candidate_price"]))
    cost_floor_price = Decimal(str(item["cost_floor_price"]))
    estimated_margin_rate = Decimal(str(item["estimated_margin_rate"]))
    checks = []

    if candidate_price < cost_floor_price:
        checks.append(
            _check(
                "BELOW_COST_FLOOR",
                "error",
                "Candidate price is below the deterministic cost floor.",
            )
        )
    else:
        checks.append(
            _check(
                "ABOVE_COST_FLOOR",
                "pass",
                "Candidate price is above the deterministic cost floor.",
            )
        )

    if cost_profile is None:
        checks.append(
            _check(
                "MISSING_COST_PROFILE",
                "error",
                "Matching cost profile is missing; validation cannot verify minimum margin.",
            )
        )
    else:
        minimum_margin_rate = Decimal(str(cost_profile["minimum_margin_rate"]))
        if estimated_margin_rate < minimum_margin_rate:
            checks.append(
                _check(
                    "MARGIN_BELOW_MINIMUM",
                    "error",
                    "Estimated margin is below the matching cost profile minimum margin.",
                )
            )
        else:
            checks.append(
                _check(
                    "MARGIN_PROTECTED",
                    "pass",
                    "Estimated margin is at or above the matching minimum margin.",
                )
            )

    market_lowest = (
        Decimal(str(item["market_lowest_price"]))
        if item["market_lowest_price"] is not None
        else None
    )
    market_average = (
        Decimal(str(item["market_average_price"]))
        if item["market_average_price"] is not None
        else None
    )

    if item["market_reference_count"] == 0 or market_lowest is None or market_average is None:
        checks.append(
            _check(
                "MISSING_MARKET_DATA",
                "warning",
                "No matching competitor reference data exists; review this quantity conservatively.",
            )
        )
    else:
        checks.append(
            _check(
                "MARKET_REFERENCE_AVAILABLE",
                "info",
                "Matching competitor reference data is available for this quantity.",
            )
        )

        if market_lowest < cost_floor_price:
            checks.append(
                _check(
                    "MARKET_LOW_BELOW_COST_FLOOR",
                    "warning",
                    "Lowest competitor reference is below cost floor and may be unsustainable.",
                )
            )

        close_to_lowest_limit = market_lowest * (Decimal("1") + LOWEST_MARKET_PROXIMITY_THRESHOLD)
        if candidate_price <= close_to_lowest_limit:
            checks.append(
                _check(
                    "TOO_CLOSE_TO_LOWEST_MARKET_PRICE",
                    "warning",
                    "Candidate is very close to the lowest competitor price; do not blindly follow the lowest reference.",
                )
            )

        below_average_limit = market_average * (Decimal("1") - MARKET_BELOW_AVERAGE_THRESHOLD)
        above_average_limit = market_average * (Decimal("1") + MARKET_ABOVE_AVERAGE_THRESHOLD)
        if candidate_price < below_average_limit:
            checks.append(
                _check(
                    "BELOW_MARKET_AVERAGE",
                    "warning",
                    "Candidate price is more than 15% below market average but still needs margin review.",
                )
            )
        elif candidate_price > above_average_limit:
            checks.append(
                _check(
                    "ABOVE_MARKET_AVERAGE",
                    "warning",
                    "Candidate price is more than 20% above market average; review positioning.",
                )
            )

    levels = [check["level"] for check in checks]
    return {
        "quantity": item["quantity"],
        "candidate_price": _money(candidate_price),
        "status": _status_for_levels(levels),
        "risk_level": _risk_for_levels(levels),
        "checks": checks,
    }


def _add_ladder_checks(results: list[dict[str, Any]], items: list[sqlite3.Row]) -> None:
    for index in range(1, len(items)):
        previous = items[index - 1]
        current = items[index]
        previous_price = Decimal(str(previous["candidate_price"]))
        current_price = Decimal(str(current["candidate_price"]))
        previous_unit_price = Decimal(str(previous["unit_price"]))
        current_unit_price = Decimal(str(current["unit_price"]))
        current_result = results[index]

        if current_price < previous_price:
            current_result["checks"].append(
                _check(
                    "TOTAL_PRICE_DECREASES_WITH_QUANTITY",
                    "error",
                    "Total candidate price decreases while quantity increases.",
                )
            )

        unit_price_limit = previous_unit_price * (Decimal("1") + UNIT_PRICE_INCREASE_THRESHOLD)
        if current_unit_price > unit_price_limit:
            current_result["checks"].append(
                _check(
                    "UNIT_PRICE_INCREASES_WITH_QUANTITY",
                    "warning",
                    "Unit price increases by more than 5% at a higher quantity.",
                )
            )

        levels = [check["level"] for check in current_result["checks"]]
        current_result["status"] = _status_for_levels(levels)
        current_result["risk_level"] = _risk_for_levels(levels)


def _build_summary(results: list[dict[str, Any]]) -> dict[str, int]:
    levels = [check["level"] for result in results for check in result["checks"]]
    return {
        "item_count": len(results),
        "pass_count": levels.count("pass"),
        "info_count": levels.count("info"),
        "warning_count": levels.count("warning"),
        "error_count": levels.count("error"),
    }


def validate_candidate_table(
    connection: sqlite3.Connection,
    *,
    candidate_table_id: int,
) -> dict[str, Any]:
    table = _fetch_candidate_table(connection, candidate_table_id)
    items = _fetch_candidate_items(connection, candidate_table_id)
    log_agent_step(
        connection,
        candidate_table_id=candidate_table_id,
        step_type="validation_run",
        title="Validation started",
        message=f"Started deterministic validation for {len(items)} candidate rows.",
        status="running",
        metadata={"item_count": len(items)},
    )

    results = []
    for item in items:
        cost_profile = _find_cost_profile(
            connection,
            table["product_id"],
            item["quantity"],
            item["option_summary"],
        )
        results.append(_validate_item(item=item, cost_profile=cost_profile))

    _add_ladder_checks(results, items)
    summary = _build_summary(results)
    if summary["error_count"] > 0:
        overall_status = "fail"
        risk_level = "high"
    elif summary["warning_count"] > 0:
        overall_status = "pass_with_warnings"
        risk_level = "medium"
    else:
        overall_status = "pass"
        risk_level = "low"

    warnings = [
        "Validation is deterministic and does not approve or activate candidate tables.",
        "Human approval is a separate explicit admin action.",
    ]
    thresholds = {
        "market_below_average_warning_rate": _rate(MARKET_BELOW_AVERAGE_THRESHOLD),
        "market_above_average_warning_rate": _rate(MARKET_ABOVE_AVERAGE_THRESHOLD),
        "lowest_market_proximity_warning_rate": _rate(LOWEST_MARKET_PROXIMITY_THRESHOLD),
        "unit_price_increase_warning_rate": _rate(UNIT_PRICE_INCREASE_THRESHOLD),
    }
    now = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO validation_results (
            candidate_table_id, overall_status, risk_level, summary_json,
            result_json, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            candidate_table_id,
            overall_status,
            risk_level,
            json.dumps(summary),
            json.dumps(results),
            now,
            now,
        ),
    )
    validation_result_id = cursor.lastrowid
    log_agent_step(
        connection,
        candidate_table_id=candidate_table_id,
        validation_result_id=validation_result_id,
        step_type="cost_floor_calculated",
        title="Cost floor checks completed",
        message="Checked candidate prices against stored deterministic cost floors.",
        metadata={"error_count": summary["error_count"]},
    )
    log_agent_step(
        connection,
        candidate_table_id=candidate_table_id,
        validation_result_id=validation_result_id,
        step_type="market_reference_analyzed",
        title="Market checks completed",
        message="Checked market-low, market-average, and missing-market warnings.",
        status="warning" if summary["warning_count"] else "completed",
        metadata={"warning_count": summary["warning_count"]},
    )
    log_agent_step(
        connection,
        candidate_table_id=candidate_table_id,
        validation_result_id=validation_result_id,
        step_type="validation_run",
        title="Quantity ladder checks completed",
        message="Checked total price and unit price movement across quantities.",
        metadata={"item_count": summary["item_count"]},
    )
    if summary["warning_count"] or summary["error_count"]:
        log_agent_step(
            connection,
            candidate_table_id=candidate_table_id,
            validation_result_id=validation_result_id,
            step_type="warning_detected",
            title="Validation warnings detected",
            message=(
                f"Detected {summary['warning_count']} warnings and "
                f"{summary['error_count']} errors."
            ),
            status="error" if summary["error_count"] else "warning",
            metadata=summary,
        )
    log_agent_step(
        connection,
        candidate_table_id=candidate_table_id,
        validation_result_id=validation_result_id,
        step_type="validation_run",
        title="Validation completed",
        message=f"Validation finished with status {overall_status} and risk {risk_level}.",
        status="error" if overall_status == "fail" else "completed",
        metadata={"overall_status": overall_status, "risk_level": risk_level},
    )

    return {
        "validation_result_id": validation_result_id,
        "candidate_table_id": candidate_table_id,
        "candidate_table_name": table["name"],
        "overall_status": overall_status,
        "risk_level": risk_level,
        "summary": summary,
        "results": results,
        "thresholds": thresholds,
        "warnings": warnings,
    }
