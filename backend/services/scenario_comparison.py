from __future__ import annotations

import json
import sqlite3
from statistics import mean
from typing import Any


class ScenarioComparisonError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _normalize(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _round_money(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


def _round_rate(value: float | None) -> float | None:
    return round(value, 4) if value is not None else None


def _validation_summary(connection: sqlite3.Connection, candidate_table_id: int | None) -> dict[str, Any] | None:
    if candidate_table_id is None:
        return None
    row = connection.execute(
        """
        SELECT id, overall_status, risk_level, summary_json, result_json, created_at
        FROM validation_results
        WHERE candidate_table_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (candidate_table_id,),
    ).fetchone()
    if row is None:
        return None

    summary = json.loads(row["summary_json"] or "{}")
    results = json.loads(row["result_json"] or "[]")
    quantity_statuses = {
        int(result["quantity"]): {
            "status": result.get("status"),
            "risk_level": result.get("risk_level"),
        }
        for result in results
        if "quantity" in result
    }
    return {
        "validation_result_id": int(row["id"]),
        "overall_status": row["overall_status"],
        "risk_level": row["risk_level"],
        "summary": summary,
        "latest_validation_at": row["created_at"],
        "quantity_statuses": quantity_statuses,
    }


def _approval_readiness(
    *,
    scenario_type: str,
    status: str,
    validation: dict[str, Any] | None,
    active_table_exists: bool,
) -> dict[str, Any]:
    if scenario_type == "price_table":
        return {
            "scenario_type": scenario_type,
            "is_candidate": False,
            "approval_required": False,
            "ready_for_owner_review": False,
            "status": status,
            "reason_codes": ["PRICE_TABLE_ALREADY_INTERNAL"],
            "message": "Internal price tables are compared for review only; comparison does not change activation.",
        }

    reason_codes = ["HUMAN_OWNER_APPROVAL_REQUIRED"]
    validation_exists = validation is not None
    has_validation_failures = validation_exists and validation["overall_status"] == "fail"
    pending_status = status in {"generated", "reviewed"}

    if not validation_exists:
        reason_codes.append("MISSING_VALIDATION_RESULT")
    elif has_validation_failures:
        reason_codes.append("VALIDATION_FAILED")
    else:
        reason_codes.append("VALIDATION_READY_FOR_REVIEW")

    if status == "approved":
        reason_codes.append("CANDIDATE_ALREADY_APPROVED")
    elif status == "rejected":
        reason_codes.append("CANDIDATE_ALREADY_REJECTED")
    elif pending_status:
        reason_codes.append("CANDIDATE_PENDING_OWNER_REVIEW")

    if not active_table_exists:
        reason_codes.append("NO_ACTIVE_PRICE_TABLE")

    ready = pending_status and validation_exists and not has_validation_failures
    return {
        "scenario_type": scenario_type,
        "is_candidate": True,
        "approval_required": True,
        "owner_approval_required": True,
        "ready_for_owner_review": ready,
        "validation_exists": validation_exists,
        "has_validation_failures": has_validation_failures,
        "candidate_status": status,
        "active_price_table_exists": active_table_exists,
        "reason_codes": reason_codes,
        "message": "Owner must review this candidate manually before it can become active.",
    }


def _fetch_price_table(connection: sqlite3.Connection, scenario_id: int) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT pt.id, pt.product_id, pt.name, pt.status, pt.strategy_name,
               pt.created_at, pt.updated_at, p.name AS product_name
        FROM price_tables pt
        JOIN products p ON p.id = pt.product_id
        WHERE pt.id = ?
        """,
        (scenario_id,),
    ).fetchone()
    if row is None:
        raise ScenarioComparisonError(404, "Price table scenario not found.")
    return row


def _fetch_candidate_table(connection: sqlite3.Connection, scenario_id: int) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT ct.id, ct.product_id, ct.name, ct.status, ct.strategy_name,
               ct.created_at, ct.updated_at, p.name AS product_name
        FROM candidate_tables ct
        JOIN products p ON p.id = ct.product_id
        WHERE ct.id = ?
        """,
        (scenario_id,),
    ).fetchone()
    if row is None:
        raise ScenarioComparisonError(404, "Candidate table scenario not found.")
    return row


def _active_table_exists(connection: sqlite3.Connection, product_id: int) -> bool:
    row = connection.execute(
        "SELECT id FROM price_tables WHERE product_id = ? AND status = 'active' LIMIT 1",
        (product_id,),
    ).fetchone()
    return row is not None


def _load_price_table_items(connection: sqlite3.Connection, scenario_id: int) -> dict[tuple[int, str], dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT quantity, option_summary, final_price, margin_rate
        FROM price_table_items
        WHERE price_table_id = ?
        ORDER BY quantity, id
        """,
        (scenario_id,),
    ).fetchall()
    return {
        (int(row["quantity"]), _normalize(row["option_summary"])): {
            "quantity": int(row["quantity"]),
            "option_summary": row["option_summary"],
            "price": float(row["final_price"]),
            "margin_rate": float(row["margin_rate"]),
        }
        for row in rows
    }


def _load_candidate_items(connection: sqlite3.Connection, scenario_id: int) -> dict[tuple[int, str], dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT quantity, option_summary, candidate_price, estimated_margin_rate
        FROM candidate_table_items
        WHERE candidate_table_id = ?
        ORDER BY quantity, id
        """,
        (scenario_id,),
    ).fetchall()
    return {
        (int(row["quantity"]), _normalize(row["option_summary"])): {
            "quantity": int(row["quantity"]),
            "option_summary": row["option_summary"],
            "price": float(row["candidate_price"]),
            "margin_rate": float(row["estimated_margin_rate"]),
        }
        for row in rows
    }


def _load_scenario(
    connection: sqlite3.Connection,
    *,
    scenario_type: str,
    scenario_id: int,
) -> dict[str, Any]:
    if scenario_type == "price_table":
        table = _fetch_price_table(connection, scenario_id)
        items = _load_price_table_items(connection, scenario_id)
        candidate_table_id = None
    elif scenario_type == "candidate_table":
        table = _fetch_candidate_table(connection, scenario_id)
        items = _load_candidate_items(connection, scenario_id)
        candidate_table_id = scenario_id
    else:
        raise ScenarioComparisonError(
            400,
            "scenario_type must be one of: price_table, candidate_table.",
        )

    validation = _validation_summary(connection, candidate_table_id)
    active_exists = _active_table_exists(connection, int(table["product_id"]))
    approval_readiness = _approval_readiness(
        scenario_type=scenario_type,
        status=table["status"],
        validation=validation,
        active_table_exists=active_exists,
    )
    return {
        "scenario_type": scenario_type,
        "scenario_id": scenario_id,
        "candidate_table_id": candidate_table_id,
        "product_id": int(table["product_id"]),
        "product_name": table["product_name"],
        "name": table["name"],
        "status": table["status"],
        "strategy_name": table["strategy_name"],
        "created_at": table["created_at"],
        "latest_updated_at": table["updated_at"],
        "items": items,
        "validation": validation,
        "approval_readiness": approval_readiness,
    }


def _scenario_summary(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "scenario_type": scenario["scenario_type"],
        "scenario_id": scenario["scenario_id"],
        "product_id": scenario["product_id"],
        "product_name": scenario["product_name"],
        "name": scenario["name"],
        "status": scenario["status"],
        "strategy_name": scenario["strategy_name"],
        "item_count": len(scenario["items"]),
        "latest_updated_at": scenario["latest_updated_at"],
        "validation": (
            {
                key: value
                for key, value in scenario["validation"].items()
                if key != "quantity_statuses"
            }
            if scenario["validation"]
            else None
        ),
        "approval_readiness": scenario["approval_readiness"],
    }


def compare_pricing_scenarios(
    connection: sqlite3.Connection,
    *,
    base_type: str,
    base_id: int,
    compare_type: str,
    compare_id: int,
) -> dict[str, Any]:
    base = _load_scenario(connection, scenario_type=base_type, scenario_id=base_id)
    compare = _load_scenario(connection, scenario_type=compare_type, scenario_id=compare_id)
    if base["product_id"] != compare["product_id"]:
        raise ScenarioComparisonError(400, "Scenarios must belong to the same product.")

    item_keys = sorted(
        set(base["items"]) | set(compare["items"]),
        key=lambda key: (key[0], base["items"].get(key, compare["items"].get(key, {})).get("option_summary", "")),
    )
    if not item_keys:
        raise ScenarioComparisonError(404, "No scenario items were found to compare.")

    price_differences: list[float] = []
    price_difference_rates: list[float] = []
    margin_differences: list[float] = []
    warnings: set[str] = set()
    item_differences = []

    base_quantity_statuses = (base["validation"] or {}).get("quantity_statuses", {})
    compare_quantity_statuses = (compare["validation"] or {}).get("quantity_statuses", {})

    for key in item_keys:
        base_item = base["items"].get(key)
        compare_item = compare["items"].get(key)
        quantity = key[0]
        option_summary = (
            compare_item["option_summary"]
            if compare_item is not None
            else base_item["option_summary"]
        )
        base_price = base_item["price"] if base_item else None
        compare_price = compare_item["price"] if compare_item else None
        base_margin = base_item["margin_rate"] if base_item else None
        compare_margin = compare_item["margin_rate"] if compare_item else None
        price_difference = None
        price_difference_rate = None
        margin_difference = None
        row_warnings = []

        if base_item is None:
            row_warnings.append("MISSING_BASE_ITEM")
        if compare_item is None:
            row_warnings.append("MISSING_COMPARE_ITEM")

        if base_price is not None and compare_price is not None:
            price_difference = compare_price - base_price
            price_differences.append(price_difference)
            if base_price != 0:
                price_difference_rate = price_difference / base_price
                price_difference_rates.append(price_difference_rate)

        if base_margin is not None and compare_margin is not None:
            margin_difference = compare_margin - base_margin
            margin_differences.append(margin_difference)
        else:
            row_warnings.append("MISSING_MARGIN_DATA")

        warnings.update(row_warnings)
        if base_item is None:
            match_status = "missing_base"
        elif compare_item is None:
            match_status = "missing_compare"
        elif price_difference == 0:
            match_status = "unchanged"
        elif price_difference is not None and price_difference > 0:
            match_status = "price_increased"
        else:
            match_status = "price_decreased"

        item_differences.append(
            {
                "quantity": quantity,
                "option_summary": option_summary,
                "match_status": match_status,
                "base_price": base_price,
                "compare_price": compare_price,
                "price_difference": _round_money(price_difference),
                "price_difference_rate": _round_rate(price_difference_rate),
                "base_margin_rate": _round_rate(base_margin),
                "compare_margin_rate": _round_rate(compare_margin),
                "margin_difference": _round_rate(margin_difference),
                "base_validation_status": (base_quantity_statuses.get(quantity) or {}).get("status"),
                "compare_validation_status": (compare_quantity_statuses.get(quantity) or {}).get("status"),
                "warnings": row_warnings,
            }
        )

    matching_count = sum(1 for item in item_differences if item["match_status"] not in {"missing_base", "missing_compare"})
    missing_count = len(item_differences) - matching_count
    increased_count = sum(1 for item in item_differences if item["match_status"] == "price_increased")
    decreased_count = sum(1 for item in item_differences if item["match_status"] == "price_decreased")
    unchanged_count = sum(1 for item in item_differences if item["match_status"] == "unchanged")

    validation_notes = []
    if base["validation"] is None:
        validation_notes.append("Base scenario has no saved validation result.")
    if compare["validation"] is None:
        validation_notes.append("Compare scenario has no saved validation result.")

    approval_notes = [
        "Scenario comparison is read-only and never approves or activates candidate tables.",
        "Owner approval is still required for candidate activation.",
    ]
    if base["approval_readiness"].get("ready_for_owner_review"):
        approval_notes.append("Base candidate is ready for owner review based on saved validation status.")
    if compare["approval_readiness"].get("ready_for_owner_review"):
        approval_notes.append("Compare candidate is ready for owner review based on saved validation status.")

    top_level_warnings = sorted(warnings)
    if missing_count:
        top_level_warnings.append("ITEM_MATCH_GAPS")
    if validation_notes:
        top_level_warnings.append("MISSING_VALIDATION_DATA")

    return {
        "base": _scenario_summary(base),
        "compare": _scenario_summary(compare),
        "summary": {
            "total_compared_items": len(item_differences),
            "matching_item_count": matching_count,
            "missing_item_count": missing_count,
            "average_price_difference": _round_money(mean(price_differences)) if price_differences else None,
            "min_price_difference": _round_money(min(price_differences)) if price_differences else None,
            "max_price_difference": _round_money(max(price_differences)) if price_differences else None,
            "average_price_difference_rate": _round_rate(mean(price_difference_rates)) if price_difference_rates else None,
            "average_margin_difference": _round_rate(mean(margin_differences)) if margin_differences else None,
            "price_increase_count": increased_count,
            "price_decrease_count": decreased_count,
            "unchanged_count": unchanged_count,
            "warning_count": sum(len(item["warnings"]) for item in item_differences) + len(validation_notes),
        },
        "item_differences": item_differences,
        "validation_comparison": {
            "base": _scenario_summary(base)["validation"],
            "compare": _scenario_summary(compare)["validation"],
            "notes": validation_notes,
        },
        "approval_readiness": {
            "base": base["approval_readiness"],
            "compare": compare["approval_readiness"],
            "notes": approval_notes,
        },
        "warnings": top_level_warnings,
        "notes": [
            "All scenario comparison numbers come from stored price table items, candidate table items, and saved validation results.",
            "AI does not generate comparison numbers, margins, validation results, or approval decisions.",
            "This endpoint is read-only and does not approve, reject, archive, or activate price tables.",
        ],
    }
