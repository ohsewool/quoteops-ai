from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any


RECENT_WINDOW_DAYS = 7


def _count(
    connection: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> int:
    row = connection.execute(sql, params).fetchone()
    return int(row[0] if row else 0)


def _status_counts(
    connection: sqlite3.Connection,
    table_name: str,
    status_column: str,
    statuses: list[str],
) -> dict[str, int]:
    rows = connection.execute(
        f"""
        SELECT {status_column} AS status, COUNT(*) AS count
        FROM {table_name}
        GROUP BY {status_column}
        """
    ).fetchall()
    counts = {status: 0 for status in statuses}
    for row in rows:
        status = row["status"]
        if status in counts:
            counts[status] = int(row["count"])
    return counts


def _chart_from_counts(counts: dict[str, int], order: list[str]) -> list[dict[str, int | str]]:
    return [{"name": name, "value": int(counts.get(name, 0))} for name in order]


def get_dashboard_kpis(connection: sqlite3.Connection) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc)
    recent_cutoff = (generated_at - timedelta(days=RECENT_WINDOW_DAYS)).isoformat()

    price_table_statuses = ["draft", "active", "archived"]
    candidate_statuses = ["generated", "reviewed", "approved", "rejected", "discarded"]
    validation_statuses = ["pass", "pass_with_warnings", "fail"]
    quote_request_statuses = ["submitted", "reviewing", "quoted", "rejected", "archived"]
    workflow_statuses = ["queued", "running", "completed", "failed", "cancelled"]

    price_table_counts = _status_counts(
        connection,
        "price_tables",
        "status",
        price_table_statuses,
    )
    candidate_counts = _status_counts(
        connection,
        "candidate_tables",
        "status",
        candidate_statuses,
    )
    validation_counts = _status_counts(
        connection,
        "validation_results",
        "overall_status",
        validation_statuses,
    )
    quote_request_counts = _status_counts(
        connection,
        "quote_requests",
        "status",
        quote_request_statuses,
    )
    workflow_counts = _status_counts(
        connection,
        "agent_jobs",
        "status",
        workflow_statuses,
    )

    total_csv_imports = _count(
        connection,
        """
        SELECT COUNT(*)
        FROM audit_logs
        WHERE action IN ('csv_import_completed', 'csv_import_failed')
        """,
    )
    failed_csv_imports = _count(
        connection,
        "SELECT COUNT(*) FROM audit_logs WHERE action = 'csv_import_failed'",
    )

    notes = [
        "All KPI values are calculated from persisted backend data.",
        "AI does not generate KPI numbers, approval decisions, or pricing values.",
        "CSV import counts are inferred from audit log completion/failure events.",
    ]

    return {
        "generated_at": generated_at.isoformat(),
        "recent_window_days": RECENT_WINDOW_DAYS,
        "pricing": {
            "total_products": _count(connection, "SELECT COUNT(*) FROM products"),
            "active_products": _count(
                connection,
                "SELECT COUNT(*) FROM products WHERE is_active = 1",
            ),
            "total_competitors": _count(connection, "SELECT COUNT(*) FROM competitors"),
            "total_competitor_prices": _count(connection, "SELECT COUNT(*) FROM competitor_prices"),
            "total_cost_profiles": _count(connection, "SELECT COUNT(*) FROM cost_profiles"),
            "total_price_tables": _count(connection, "SELECT COUNT(*) FROM price_tables"),
            "active_price_tables": price_table_counts["active"],
            "draft_price_tables": price_table_counts["draft"],
            "archived_price_tables": price_table_counts["archived"],
        },
        "candidates": {
            "total_candidate_tables": _count(connection, "SELECT COUNT(*) FROM candidate_tables"),
            "generated_candidate_tables": candidate_counts["generated"],
            "approved_candidate_tables": candidate_counts["approved"],
            "rejected_candidate_tables": candidate_counts["rejected"],
        },
        "validation": {
            "pass_count": validation_counts["pass"],
            "warning_count": validation_counts["pass_with_warnings"],
            "fail_count": validation_counts["fail"],
            "high_risk_count": _count(
                connection,
                "SELECT COUNT(*) FROM validation_results WHERE risk_level = 'high'",
            ),
        },
        "quote_requests": {
            "submitted": quote_request_counts["submitted"],
            "reviewing": quote_request_counts["reviewing"],
            "quoted": quote_request_counts["quoted"],
            "rejected": quote_request_counts["rejected"],
            "archived": quote_request_counts["archived"],
        },
        "approvals": {
            "total_approvals": _count(connection, "SELECT COUNT(*) FROM approvals"),
            "recent_approvals_count": _count(
                connection,
                "SELECT COUNT(*) FROM approvals WHERE created_at >= ?",
                (recent_cutoff,),
            ),
        },
        "operations": {
            "total_audit_logs": _count(connection, "SELECT COUNT(*) FROM audit_logs"),
            "recent_audit_logs_count": _count(
                connection,
                "SELECT COUNT(*) FROM audit_logs WHERE created_at >= ?",
                (recent_cutoff,),
            ),
            "total_csv_imports": total_csv_imports,
            "failed_csv_imports": failed_csv_imports,
            "total_workflow_jobs": _count(connection, "SELECT COUNT(*) FROM agent_jobs"),
            "completed_workflow_jobs": workflow_counts["completed"],
            "failed_workflow_jobs": workflow_counts["failed"],
        },
        "charts": {
            "price_table_status": _chart_from_counts(price_table_counts, price_table_statuses),
            "candidate_status": _chart_from_counts(candidate_counts, candidate_statuses),
            "validation_status": _chart_from_counts(validation_counts, validation_statuses),
            "quote_request_status": _chart_from_counts(
                quote_request_counts,
                quote_request_statuses,
            ),
            "workflow_job_status": _chart_from_counts(workflow_counts, workflow_statuses),
        },
        "notes": notes,
    }
