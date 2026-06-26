from __future__ import annotations

import json
import sqlite3
from typing import Any

from backend.db import utc_now
from backend.schemas.jobs import PricingAnalysisWorkflowRequest
from backend.services.audit_logger import audit_actor, log_audit_event
from backend.services.candidate_generator import generate_candidate_prices
from backend.services.candidate_validator import validate_candidate_table
from backend.services.explanation_service import explain_candidate_table
from backend.services.market_reference import MarketReferenceError, resolve_product


class JobWorkflowError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class JobWorkflowNotFoundError(JobWorkflowError):
    status_code = 404


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _json_loads(value: str | None) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def serialize_job(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["input"] = _json_loads(item.pop("input_json")) or {}
    item["result"] = _json_loads(item.pop("result_json"))
    return item


def serialize_step(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["metadata"] = _json_loads(item.pop("metadata_json"))
    return item


def create_agent_job(
    connection: sqlite3.Connection,
    *,
    job_type: str,
    title: str,
    input_data: dict[str, Any],
    created_by: str | None = None,
) -> int:
    now = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO agent_jobs (
            job_type, status, title, input_json, created_by,
            created_at, updated_at
        )
        VALUES (?, 'queued', ?, ?, ?, ?, ?)
        """,
        (job_type, title, _json_dumps(input_data), created_by, now, now),
    )
    return cursor.lastrowid


def update_job_status(
    connection: sqlite3.Connection,
    job_id: int,
    *,
    status: str,
    result: dict[str, Any] | None = None,
    error_message: str | None = None,
) -> None:
    now = utc_now()
    started_at_sql = ", started_at = COALESCE(started_at, ?)" if status == "running" else ""
    completed_at_sql = ", completed_at = ?" if status in {"completed", "failed", "cancelled"} else ""
    values: list[Any] = [status, now, _json_dumps(result) if result is not None else None, error_message]
    if status == "running":
        values.append(now)
    if status in {"completed", "failed", "cancelled"}:
        values.append(now)
    values.append(job_id)
    connection.execute(
        f"""
        UPDATE agent_jobs
        SET status = ?,
            updated_at = ?,
            result_json = COALESCE(?, result_json),
            error_message = ?
            {started_at_sql}
            {completed_at_sql}
        WHERE id = ?
        """,
        values,
    )


def create_job_step(
    connection: sqlite3.Connection,
    *,
    job_id: int,
    step_type: str,
    title: str,
    message: str,
    status: str = "running",
    metadata: dict[str, Any] | None = None,
) -> int:
    now = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO agent_job_steps (
            job_id, step_type, status, title, message, metadata_json,
            started_at, completed_at, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job_id,
            step_type,
            status,
            title,
            message,
            _json_dumps(metadata or {}),
            now if status == "running" else None,
            now if status in {"completed", "failed", "cancelled"} else None,
            now,
        ),
    )
    return cursor.lastrowid


def update_job_step(
    connection: sqlite3.Connection,
    step_id: int,
    *,
    status: str,
    message: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    now = utc_now()
    connection.execute(
        """
        UPDATE agent_job_steps
        SET status = ?,
            message = COALESCE(?, message),
            metadata_json = COALESCE(?, metadata_json),
            completed_at = CASE WHEN ? IN ('completed', 'failed', 'cancelled') THEN ? ELSE completed_at END
        WHERE id = ?
        """,
        (
            status,
            message,
            _json_dumps(metadata) if metadata is not None else None,
            status,
            now,
            step_id,
        ),
    )


def get_job(connection: sqlite3.Connection, job_id: int) -> dict[str, Any]:
    row = connection.execute(
        """
        SELECT
            id, job_type, status, title, input_json, result_json, error_message,
            created_by, created_at, updated_at, started_at, completed_at
        FROM agent_jobs
        WHERE id = ?
        """,
        (job_id,),
    ).fetchone()
    if row is None:
        raise JobWorkflowNotFoundError("Job not found.")
    return serialize_job(row)


def list_jobs(
    connection: sqlite3.Connection,
    *,
    status: str | None = None,
    job_type: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    where = []
    values: list[Any] = []
    if status:
        where.append("status = ?")
        values.append(status)
    if job_type:
        where.append("job_type = ?")
        values.append(job_type)
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = connection.execute(
        f"SELECT COUNT(*) FROM agent_jobs {where_clause}",
        values,
    ).fetchone()[0]
    rows = connection.execute(
        f"""
        SELECT
            id, job_type, status, title, input_json, result_json, error_message,
            created_by, created_at, updated_at, started_at, completed_at
        FROM agent_jobs
        {where_clause}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        [*values, limit, offset],
    ).fetchall()
    return {
        "items": [serialize_job(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def list_job_steps(connection: sqlite3.Connection, job_id: int) -> list[dict[str, Any]]:
    get_job(connection, job_id)
    rows = connection.execute(
        """
        SELECT
            id, job_id, step_type, status, title, message, metadata_json,
            started_at, completed_at, created_at
        FROM agent_job_steps
        WHERE job_id = ?
        ORDER BY id ASC
        """,
        (job_id,),
    ).fetchall()
    return [serialize_step(row) for row in rows]


def _count_agent_logs(
    connection: sqlite3.Connection,
    *,
    pricing_session_id: int | None,
    candidate_table_id: int | None,
) -> int:
    if pricing_session_id is not None and candidate_table_id is not None:
        return connection.execute(
            """
            SELECT COUNT(*)
            FROM agent_logs
            WHERE pricing_session_id = ?
                OR candidate_table_id = ?
            """,
            (pricing_session_id, candidate_table_id),
        ).fetchone()[0]
    if pricing_session_id is not None:
        return connection.execute(
            "SELECT COUNT(*) FROM agent_logs WHERE pricing_session_id = ?",
            (pricing_session_id,),
        ).fetchone()[0]
    if candidate_table_id is not None:
        return connection.execute(
            "SELECT COUNT(*) FROM agent_logs WHERE candidate_table_id = ?",
            (candidate_table_id,),
        ).fetchone()[0]
    return 0


def _count_workflow_audit_logs(connection: sqlite3.Connection, job_id: int) -> int:
    return connection.execute(
        """
        SELECT COUNT(*)
        FROM audit_logs
        WHERE metadata_json LIKE ?
        """,
        (f'%"job_id": {job_id}%',),
    ).fetchone()[0]


def _complete_step(
    connection: sqlite3.Connection,
    step_id: int,
    *,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    update_job_step(connection, step_id, status="completed", message=message, metadata=metadata)


def _fail_workflow(
    connection: sqlite3.Connection,
    *,
    job_id: int,
    step_id: int | None,
    detail: str,
    admin: dict[str, Any] | None,
) -> dict[str, Any]:
    if step_id is not None:
        update_job_step(
            connection,
            step_id,
            status="failed",
            message=detail,
            metadata={"error": detail},
        )
    update_job_status(connection, job_id, status="failed", error_message=detail)
    log_audit_event(
        connection,
        action="workflow_job_failed",
        entity_type="agent_job",
        entity_id=job_id,
        entity_label=f"Pricing analysis job #{job_id}",
        metadata={"job_id": job_id, "error": detail},
        **audit_actor(admin),
    )
    return {
        "job": get_job(connection, job_id),
        "steps": list_job_steps(connection, job_id),
    }


def run_pricing_analysis_workflow(
    connection: sqlite3.Connection,
    *,
    request: PricingAnalysisWorkflowRequest,
    admin: dict[str, Any] | None = None,
) -> dict[str, Any]:
    input_data = request.model_dump()
    job_id = create_agent_job(
        connection,
        job_type="pricing_analysis",
        title="Pricing analysis workflow",
        input_data=input_data,
        created_by=(admin.get("display_name") or admin.get("email")) if admin else None,
    )
    log_audit_event(
        connection,
        action="workflow_job_created",
        entity_type="agent_job",
        entity_id=job_id,
        entity_label=f"Pricing analysis job #{job_id}",
        metadata={"job_id": job_id, "input": input_data},
        **audit_actor(admin),
    )
    update_job_status(connection, job_id, status="running")

    current_step_id: int | None = None
    candidate_result: dict[str, Any] | None = None
    validation_result: dict[str, Any] | None = None
    explanation_result: dict[str, Any] | None = None

    try:
        current_step_id = create_job_step(
            connection,
            job_id=job_id,
            step_type="load_product",
            title="Load product",
            message="Loading the product for deterministic pricing analysis.",
        )
        try:
            product = resolve_product(connection, request.product_id, request.product_slug)
        except MarketReferenceError as exc:
            raise JobWorkflowNotFoundError(exc.detail) from exc
        _complete_step(
            connection,
            current_step_id,
            message=f"Loaded product {product['name']}.",
            metadata={"product_id": product["id"], "product_name": product["name"]},
        )

        placeholders = ",".join("?" for _ in request.quantities)
        current_step_id = create_job_step(
            connection,
            job_id=job_id,
            step_type="load_cost_profiles",
            title="Load cost profiles",
            message="Checking matching cost profiles before candidate generation.",
        )
        cost_profile_count = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM cost_profiles
            WHERE product_id = ?
                AND quantity IN ({placeholders})
                AND LOWER(TRIM(option_summary)) = LOWER(TRIM(?))
            """,
            [product["id"], *request.quantities, request.option_summary],
        ).fetchone()[0]
        _complete_step(
            connection,
            current_step_id,
            message=f"Found {cost_profile_count} matching cost profile rows.",
            metadata={"cost_profile_count": cost_profile_count},
        )

        current_step_id = create_job_step(
            connection,
            job_id=job_id,
            step_type="load_market_reference",
            title="Load market references",
            message="Checking manually entered competitor references.",
        )
        market_reference_count = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM competitor_prices
            WHERE product_id = ?
                AND quantity IN ({placeholders})
                AND LOWER(TRIM(option_summary)) = LOWER(TRIM(?))
            """,
            [product["id"], *request.quantities, request.option_summary],
        ).fetchone()[0]
        _complete_step(
            connection,
            current_step_id,
            message=f"Found {market_reference_count} matching competitor reference rows.",
            metadata={"market_reference_count": market_reference_count},
        )

        current_step_id = create_job_step(
            connection,
            job_id=job_id,
            step_type="generate_candidate_table",
            title="Generate candidate table",
            message="Running existing deterministic candidate generation.",
        )
        candidate_result = generate_candidate_prices(
            connection,
            product_id=product["id"],
            option_summary=request.option_summary,
            quantities=request.quantities,
            strategy_name=request.strategy_name,
            strategy_template_id=request.strategy_template_id,
        )
        log_audit_event(
            connection,
            action="candidate_table_generated",
            entity_type="candidate_table",
            entity_id=candidate_result["candidate_table_id"],
            entity_label=candidate_result["candidate_table_name"],
            metadata={"job_id": job_id, "workflow": "pricing_analysis"},
            **audit_actor(admin),
        )
        _complete_step(
            connection,
            current_step_id,
            message="Candidate table generated. It is not active.",
            metadata={
                "candidate_table_id": candidate_result["candidate_table_id"],
                "pricing_session_id": candidate_result["pricing_session_id"],
                "item_count": candidate_result["summary"]["item_count"],
            },
        )

        if request.run_validation:
            current_step_id = create_job_step(
                connection,
                job_id=job_id,
                step_type="run_validation",
                title="Run validation",
                message="Running existing deterministic validation checks.",
            )
            validation_result = validate_candidate_table(
                connection,
                candidate_table_id=candidate_result["candidate_table_id"],
            )
            log_audit_event(
                connection,
                action="candidate_table_validated",
                entity_type="candidate_table",
                entity_id=candidate_result["candidate_table_id"],
                entity_label=candidate_result["candidate_table_name"],
                metadata={
                    "job_id": job_id,
                    "workflow": "pricing_analysis",
                    "validation_result_id": validation_result["validation_result_id"],
                    "overall_status": validation_result["overall_status"],
                    "risk_level": validation_result["risk_level"],
                },
                **audit_actor(admin),
            )
            _complete_step(
                connection,
                current_step_id,
                message=f"Validation completed with {validation_result['overall_status']}.",
                metadata={
                    "validation_result_id": validation_result["validation_result_id"],
                    "overall_status": validation_result["overall_status"],
                    "risk_level": validation_result["risk_level"],
                },
            )

        if request.run_ai_explanation:
            current_step_id = create_job_step(
                connection,
                job_id=job_id,
                step_type="generate_ai_explanation",
                title="Generate AI explanation",
                message="Generating explanation from existing deterministic facts.",
            )
            explanation_result = explain_candidate_table(
                connection,
                candidate_table_id=candidate_result["candidate_table_id"],
            )
            log_audit_event(
                connection,
                action="ai_explanation_generated",
                entity_type="candidate_table",
                entity_id=candidate_result["candidate_table_id"],
                entity_label=candidate_result["candidate_table_name"],
                metadata={
                    "job_id": job_id,
                    "workflow": "pricing_analysis",
                    "source": explanation_result["source"],
                    "warnings": explanation_result["warnings"],
                },
                **audit_actor(admin),
            )
            _complete_step(
                connection,
                current_step_id,
                message=f"Explanation created with source {explanation_result['source']}.",
                metadata={
                    "source": explanation_result["source"],
                    "warning_count": len(explanation_result["warnings"]),
                },
            )

        current_step_id = create_job_step(
            connection,
            job_id=job_id,
            step_type="write_agent_logs",
            title="Check Agent Timeline",
            message="Counting Agent Timeline rows recorded by existing services.",
        )
        agent_log_count = _count_agent_logs(
            connection,
            pricing_session_id=candidate_result["pricing_session_id"],
            candidate_table_id=candidate_result["candidate_table_id"],
        )
        _complete_step(
            connection,
            current_step_id,
            message=f"Agent Timeline contains {agent_log_count} rows for this workflow output.",
            metadata={"agent_log_count": agent_log_count},
        )

        current_step_id = create_job_step(
            connection,
            job_id=job_id,
            step_type="write_audit_logs",
            title="Check audit logs",
            message="Counting audit events recorded for this workflow.",
        )
        audit_log_count = _count_workflow_audit_logs(connection, job_id)
        _complete_step(
            connection,
            current_step_id,
            message=f"Audit log contains {audit_log_count} workflow-related events.",
            metadata={"audit_log_count": audit_log_count},
        )

        result = {
            "candidate_table_id": candidate_result["candidate_table_id"],
            "pricing_session_id": candidate_result["pricing_session_id"],
            "candidate_table_name": candidate_result["candidate_table_name"],
            "validation_result_id": (
                validation_result["validation_result_id"] if validation_result else None
            ),
            "validation_status": (
                validation_result["overall_status"] if validation_result else "not_run"
            ),
            "ai_explanation_source": (
                explanation_result["source"] if explanation_result else "not_run"
            ),
            "agent_log_count": agent_log_count,
            "audit_log_count": audit_log_count,
            "activated_price_table_id": None,
            "approval_required": True,
        }

        current_step_id = create_job_step(
            connection,
            job_id=job_id,
            step_type="complete_workflow",
            title="Complete workflow",
            message="Persisting workflow result. Candidate table remains inactive.",
        )
        update_job_status(connection, job_id, status="completed", result=result)
        _complete_step(
            connection,
            current_step_id,
            message="Workflow completed. Human approval is still required.",
            metadata=result,
        )
        log_audit_event(
            connection,
            action="workflow_job_completed",
            entity_type="agent_job",
            entity_id=job_id,
            entity_label=f"Pricing analysis job #{job_id}",
            metadata={"job_id": job_id, "result": result},
            **audit_actor(admin),
        )
        return {
            "job": get_job(connection, job_id),
            "steps": list_job_steps(connection, job_id),
        }
    except Exception as exc:
        detail = getattr(exc, "detail", str(exc))
        return _fail_workflow(
            connection,
            job_id=job_id,
            step_id=current_step_id,
            detail=detail,
            admin=admin,
        )
