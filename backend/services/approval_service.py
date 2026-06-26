from __future__ import annotations

import json
import sqlite3
from typing import Any

from backend.db import utc_now
from backend.services.agent_logger import log_agent_step
from backend.services.audit_logger import log_audit_event


class ApprovalError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class ApprovalNotFoundError(ApprovalError):
    status_code = 404


class ApprovalBlockedError(ApprovalError):
    status_code = 409


def _fetch_candidate_table(
    connection: sqlite3.Connection,
    candidate_table_id: int,
) -> sqlite3.Row:
    table = connection.execute(
        """
        SELECT
            ct.id, ct.pricing_session_id, ct.product_id, ct.name,
            ct.strategy_name, ct.status, p.name AS product_name
        FROM candidate_tables ct
        JOIN products p ON p.id = ct.product_id
        WHERE ct.id = ?
        """,
        (candidate_table_id,),
    ).fetchone()
    if table is None:
        raise ApprovalNotFoundError("Candidate table not found.")
    return table


def _fetch_candidate_items(
    connection: sqlite3.Connection,
    candidate_table_id: int,
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT
            id, quantity, option_summary, candidate_price,
            estimated_margin_rate
        FROM candidate_table_items
        WHERE candidate_table_id = ?
        ORDER BY quantity ASC, id ASC
        """,
        (candidate_table_id,),
    ).fetchall()


def _latest_validation(
    connection: sqlite3.Connection,
    candidate_table_id: int,
) -> sqlite3.Row | None:
    return connection.execute(
        """
        SELECT id, overall_status, risk_level, summary_json, result_json, created_at
        FROM validation_results
        WHERE candidate_table_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (candidate_table_id,),
    ).fetchone()


def _insert_approval(
    connection: sqlite3.Connection,
    *,
    candidate_table_id: int,
    product_id: int,
    action: str,
    status: str,
    reviewer_name: str | None,
    reviewer_note: str | None,
    created_price_table_id: int | None = None,
) -> int:
    now = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO approvals (
            candidate_table_id, product_id, action, status, reviewer_name,
            reviewer_note, created_price_table_id, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            candidate_table_id,
            product_id,
            action,
            status,
            reviewer_name,
            reviewer_note,
            created_price_table_id,
            now,
            now,
        ),
    )
    return cursor.lastrowid


def _record_blocked_approval(
    connection: sqlite3.Connection,
    *,
    table: sqlite3.Row,
    reviewer_name: str | None,
    reviewer_note: str | None,
    detail: str,
    reason_code: str,
) -> None:
    _insert_approval(
        connection,
        candidate_table_id=table["id"],
        product_id=table["product_id"],
        action="approve",
        status="failed",
        reviewer_name=reviewer_name,
        reviewer_note=reviewer_note,
    )
    log_agent_step(
        connection,
        pricing_session_id=table["pricing_session_id"],
        candidate_table_id=table["id"],
        step_type="approval_blocked_by_validation",
        title="Approval blocked",
        message=detail,
        status="error",
        metadata={"reason_code": reason_code},
    )
    connection.commit()


def _ensure_not_finalized(table: sqlite3.Row) -> None:
    if table["status"] == "approved":
        raise ApprovalBlockedError("Candidate table is already approved.")
    if table["status"] == "rejected":
        raise ApprovalBlockedError("Rejected candidate tables cannot be approved or rejected again.")


def approve_candidate_table(
    connection: sqlite3.Connection,
    *,
    candidate_table_id: int,
    reviewer_name: str | None = None,
    reviewer_note: str | None = None,
) -> dict[str, Any]:
    table = _fetch_candidate_table(connection, candidate_table_id)
    _ensure_not_finalized(table)
    items = _fetch_candidate_items(connection, candidate_table_id)

    log_agent_step(
        connection,
        pricing_session_id=table["pricing_session_id"],
        candidate_table_id=candidate_table_id,
        step_type="approval_review_started",
        title="Approval review started",
        message="Admin started human approval review for a candidate price table.",
        status="running",
        metadata={"reviewer_name": reviewer_name},
    )

    if not items:
        _record_blocked_approval(
            connection,
            table=table,
            reviewer_name=reviewer_name,
            reviewer_note=reviewer_note,
            detail="Candidate table has no items to approve.",
            reason_code="MISSING_CANDIDATE_ITEMS",
        )
        raise ApprovalBlockedError("Candidate table has no items to approve.")

    validation = _latest_validation(connection, candidate_table_id)
    if validation is None:
        _record_blocked_approval(
            connection,
            table=table,
            reviewer_name=reviewer_name,
            reviewer_note=reviewer_note,
            detail="Approval requires a saved validation result before activation.",
            reason_code="MISSING_VALIDATION_RESULT",
        )
        raise ApprovalBlockedError("Approval requires a saved validation result before activation.")

    if validation["overall_status"] == "fail":
        _record_blocked_approval(
            connection,
            table=table,
            reviewer_name=reviewer_name,
            reviewer_note=reviewer_note,
            detail="Approval is blocked because the latest validation result failed.",
            reason_code="VALIDATION_FAILED",
        )
        raise ApprovalBlockedError("Approval is blocked because the latest validation result failed.")

    now = utc_now()
    previous_active_tables = connection.execute(
        """
        SELECT id, name
        FROM price_tables
        WHERE product_id = ? AND status = 'active'
        ORDER BY id ASC
        """,
        (table["product_id"],),
    ).fetchall()
    connection.execute(
        """
        UPDATE price_tables
        SET status = 'archived', updated_at = ?
        WHERE product_id = ? AND status = 'active'
        """,
        (now, table["product_id"]),
    )

    cursor = connection.execute(
        """
        INSERT INTO price_tables (product_id, name, status, strategy_name, created_at, updated_at)
        VALUES (?, ?, 'active', ?, ?, ?)
        """,
        (
            table["product_id"],
            f"Approved candidate #{candidate_table_id} - {table['product_name']}",
            table["strategy_name"],
            now,
            now,
        ),
    )
    created_price_table_id = cursor.lastrowid

    connection.executemany(
        """
        INSERT INTO price_table_items (
            price_table_id, quantity, option_summary, final_price,
            margin_rate, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                created_price_table_id,
                item["quantity"],
                item["option_summary"],
                item["candidate_price"],
                item["estimated_margin_rate"],
                now,
                now,
            )
            for item in items
        ],
    )

    connection.execute(
        """
        UPDATE candidate_tables
        SET status = 'approved', updated_at = ?
        WHERE id = ?
        """,
        (now, candidate_table_id),
    )
    connection.execute(
        """
        UPDATE pricing_sessions
        SET status = 'approved', updated_at = ?
        WHERE id = ?
        """,
        (now, table["pricing_session_id"]),
    )
    approval_id = _insert_approval(
        connection,
        candidate_table_id=candidate_table_id,
        product_id=table["product_id"],
        action="approve",
        status="completed",
        reviewer_name=reviewer_name,
        reviewer_note=reviewer_note,
        created_price_table_id=created_price_table_id,
    )

    for previous in previous_active_tables:
        log_audit_event(
            connection,
            actor_name=reviewer_name,
            action="previous_active_price_table_archived",
            entity_type="price_table",
            entity_id=previous["id"],
            entity_label=previous["name"],
            before={"id": previous["id"], "name": previous["name"], "status": "active"},
            after={"id": previous["id"], "name": previous["name"], "status": "archived"},
            metadata={
                "candidate_table_id": candidate_table_id,
                "created_price_table_id": created_price_table_id,
                "approval_id": approval_id,
            },
        )
        log_agent_step(
            connection,
            pricing_session_id=table["pricing_session_id"],
            candidate_table_id=candidate_table_id,
            validation_result_id=validation["id"],
            step_type="previous_price_table_archived",
            title="Previous active price table archived",
            message=f"Archived previous active price table #{previous['id']}.",
            metadata={"price_table_id": previous["id"], "price_table_name": previous["name"]},
        )
    log_agent_step(
        connection,
        pricing_session_id=table["pricing_session_id"],
        candidate_table_id=candidate_table_id,
        validation_result_id=validation["id"],
        step_type="price_table_activated",
        title="Approved price table activated",
        message="Copied candidate rows unchanged into a new active internal price table.",
        metadata={"created_price_table_id": created_price_table_id, "item_count": len(items)},
    )
    log_agent_step(
        connection,
        pricing_session_id=table["pricing_session_id"],
        candidate_table_id=candidate_table_id,
        validation_result_id=validation["id"],
        step_type="candidate_approved",
        title="Candidate approved",
        message="Human reviewer approved the candidate table. AI did not make this decision.",
        metadata={
            "approval_id": approval_id,
            "reviewer_name": reviewer_name,
            "validation_status": validation["overall_status"],
        },
    )

    return {
        "approval_id": approval_id,
        "candidate_table_id": candidate_table_id,
        "product_id": table["product_id"],
        "action": "approve",
        "status": "completed",
        "candidate_status": "approved",
        "created_price_table_id": created_price_table_id,
        "message": "Candidate table approved and converted into a new active price table.",
    }


def reject_candidate_table(
    connection: sqlite3.Connection,
    *,
    candidate_table_id: int,
    reviewer_name: str | None = None,
    reviewer_note: str | None = None,
) -> dict[str, Any]:
    table = _fetch_candidate_table(connection, candidate_table_id)
    _ensure_not_finalized(table)
    now = utc_now()

    log_agent_step(
        connection,
        pricing_session_id=table["pricing_session_id"],
        candidate_table_id=candidate_table_id,
        step_type="approval_review_started",
        title="Rejection review started",
        message="Admin started human rejection review for a candidate price table.",
        status="running",
        metadata={"reviewer_name": reviewer_name},
    )
    connection.execute(
        """
        UPDATE candidate_tables
        SET status = 'rejected', updated_at = ?
        WHERE id = ?
        """,
        (now, candidate_table_id),
    )
    connection.execute(
        """
        UPDATE pricing_sessions
        SET status = 'rejected', updated_at = ?
        WHERE id = ?
        """,
        (now, table["pricing_session_id"]),
    )
    approval_id = _insert_approval(
        connection,
        candidate_table_id=candidate_table_id,
        product_id=table["product_id"],
        action="reject",
        status="completed",
        reviewer_name=reviewer_name,
        reviewer_note=reviewer_note,
    )
    log_agent_step(
        connection,
        pricing_session_id=table["pricing_session_id"],
        candidate_table_id=candidate_table_id,
        step_type="candidate_rejected",
        title="Candidate rejected",
        message="Human reviewer rejected the candidate table. No active price table was changed.",
        status="warning",
        metadata={"approval_id": approval_id, "reviewer_name": reviewer_name},
    )

    return {
        "approval_id": approval_id,
        "candidate_table_id": candidate_table_id,
        "product_id": table["product_id"],
        "action": "reject",
        "status": "completed",
        "candidate_status": "rejected",
        "created_price_table_id": None,
        "message": "Candidate table rejected. No active price table was changed.",
    }


def list_approvals(
    connection: sqlite3.Connection,
    *,
    candidate_table_id: int | None = None,
    product_id: int | None = None,
    action: str | None = None,
) -> list[dict[str, Any]]:
    where = []
    values: list[Any] = []
    if candidate_table_id is not None:
        where.append("a.candidate_table_id = ?")
        values.append(candidate_table_id)
    if product_id is not None:
        where.append("a.product_id = ?")
        values.append(product_id)
    if action:
        where.append("a.action = ?")
        values.append(action)

    query = """
        SELECT
            a.id, a.candidate_table_id, a.product_id, p.name AS product_name,
            a.action, a.status, a.reviewer_name, a.reviewer_note,
            a.created_price_table_id, a.created_at, a.updated_at
        FROM approvals a
        JOIN products p ON p.id = a.product_id
    """
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY a.id DESC"

    rows = connection.execute(query, values).fetchall()
    return [dict(row) for row in rows]
