from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from backend.config import get_settings


RECENT_WINDOW_DAYS = 7


def _count(
    connection: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> int:
    row = connection.execute(sql, params).fetchone()
    return int(row[0] if row else 0)


def _scalar(
    connection: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> Any:
    row = connection.execute(sql, params).fetchone()
    return row[0] if row else None


def _section(count: int) -> dict[str, Any]:
    return {
        "exists": count > 0,
        "count": count,
        "status": "ready" if count > 0 else "missing",
    }


def _attention(
    items: list[dict[str, Any]],
    *,
    severity: str,
    title: str,
    message: str,
    related_area: str,
    count: int | None = None,
    route: str | None = None,
) -> None:
    items.append(
        {
            "severity": severity,
            "title": title,
            "message": message,
            "related_area": related_area,
            "count": count,
            "route": route,
        }
    )


def _database_type() -> str:
    settings = get_settings()
    if settings.is_sqlite:
        return "sqlite"
    if settings.is_postgres:
        return "postgresql"
    return "unsupported"


def get_dashboard_insights(connection: sqlite3.Connection) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc)
    recent_cutoff = (generated_at - timedelta(days=RECENT_WINDOW_DAYS)).isoformat()
    settings = get_settings()

    products = _count(connection, "SELECT COUNT(*) FROM products")
    active_products = _count(connection, "SELECT COUNT(*) FROM products WHERE is_active = 1")
    competitors = _count(connection, "SELECT COUNT(*) FROM competitors")
    competitor_prices = _count(connection, "SELECT COUNT(*) FROM competitor_prices")
    cost_profiles = _count(connection, "SELECT COUNT(*) FROM cost_profiles")
    price_tables = _count(connection, "SELECT COUNT(*) FROM price_tables")
    active_price_tables = _count(connection, "SELECT COUNT(*) FROM price_tables WHERE status = 'active'")
    draft_price_tables = _count(connection, "SELECT COUNT(*) FROM price_tables WHERE status = 'draft'")
    candidate_tables = _count(connection, "SELECT COUNT(*) FROM candidate_tables")
    pending_candidates = _count(connection, "SELECT COUNT(*) FROM candidate_tables WHERE status IN ('generated', 'reviewed')")
    recently_approved_candidates = _count(
        connection,
        "SELECT COUNT(*) FROM candidate_tables WHERE status = 'approved' AND updated_at >= ?",
        (recent_cutoff,),
    )
    recently_rejected_candidates = _count(
        connection,
        "SELECT COUNT(*) FROM candidate_tables WHERE status = 'rejected' AND updated_at >= ?",
        (recent_cutoff,),
    )

    validation_pass = _count(connection, "SELECT COUNT(*) FROM validation_results WHERE overall_status = 'pass'")
    validation_warning = _count(
        connection,
        "SELECT COUNT(*) FROM validation_results WHERE overall_status = 'pass_with_warnings'",
    )
    validation_fail = _count(connection, "SELECT COUNT(*) FROM validation_results WHERE overall_status = 'fail'")
    high_risk = _count(connection, "SELECT COUNT(*) FROM validation_results WHERE risk_level = 'high'")
    latest_validation_at = _scalar(connection, "SELECT MAX(created_at) FROM validation_results")

    quote_total = _count(connection, "SELECT COUNT(*) FROM quote_requests")
    quote_submitted = _count(connection, "SELECT COUNT(*) FROM quote_requests WHERE status = 'submitted'")
    quote_reviewing = _count(connection, "SELECT COUNT(*) FROM quote_requests WHERE status = 'reviewing'")
    quote_quoted = _count(connection, "SELECT COUNT(*) FROM quote_requests WHERE status = 'quoted'")
    quote_rejected = _count(connection, "SELECT COUNT(*) FROM quote_requests WHERE status = 'rejected'")
    quote_archived = _count(connection, "SELECT COUNT(*) FROM quote_requests WHERE status = 'archived'")
    quote_recent = _count(connection, "SELECT COUNT(*) FROM quote_requests WHERE created_at >= ?", (recent_cutoff,))

    job_total = _count(connection, "SELECT COUNT(*) FROM agent_jobs")
    job_queued = _count(connection, "SELECT COUNT(*) FROM agent_jobs WHERE status = 'queued'")
    job_running = _count(connection, "SELECT COUNT(*) FROM agent_jobs WHERE status = 'running'")
    job_completed = _count(connection, "SELECT COUNT(*) FROM agent_jobs WHERE status = 'completed'")
    job_failed = _count(connection, "SELECT COUNT(*) FROM agent_jobs WHERE status = 'failed'")
    job_cancelled = _count(connection, "SELECT COUNT(*) FROM agent_jobs WHERE status = 'cancelled'")
    latest_failed_job = connection.execute(
        """
        SELECT id, title, updated_at
        FROM agent_jobs
        WHERE status = 'failed'
        ORDER BY updated_at DESC, id DESC
        LIMIT 1
        """
    ).fetchone()

    recent_audit_logs = _count(connection, "SELECT COUNT(*) FROM audit_logs WHERE created_at >= ?", (recent_cutoff,))
    recent_blocked_permissions = _count(
        connection,
        "SELECT COUNT(*) FROM audit_logs WHERE action = 'role_restricted_action_blocked' AND created_at >= ?",
        (recent_cutoff,),
    )
    recent_approval_events = _count(
        connection,
        """
        SELECT COUNT(*)
        FROM audit_logs
        WHERE action IN ('candidate_table_approved', 'candidate_table_rejected') AND created_at >= ?
        """,
        (recent_cutoff,),
    )
    latest_events = [
        dict(row)
        for row in connection.execute(
            """
            SELECT id, action, entity_type, entity_id, actor_name, actor_role, created_at
            FROM audit_logs
            ORDER BY created_at DESC, id DESC
            LIMIT 5
            """
        ).fetchall()
    ]

    data_quality = {
        "products": _section(products),
        "competitors": _section(competitors),
        "competitor_prices": _section(competitor_prices),
        "cost_profiles": _section(cost_profiles),
        "price_tables": _section(price_tables),
        "candidate_tables": _section(candidate_tables),
    }
    ready_for_pricing = all(
        data_quality[key]["exists"]
        for key in ("products", "competitors", "competitor_prices", "cost_profiles", "price_tables")
    )
    data_quality["ready_for_pricing_workflow"] = ready_for_pricing

    attention_items: list[dict[str, Any]] = []
    if pending_candidates:
        _attention(
            attention_items,
            severity="warning",
            title="승인 대기 후보 가격표",
            message="관리자 승인 전까지 후보 가격표는 실제 견적에 적용되지 않습니다.",
            related_area="approval",
            count=pending_candidates,
            route="#approval",
        )
    if validation_fail:
        _attention(
            attention_items,
            severity="critical",
            title="검증 실패 항목",
            message="검증 실패 후보는 승인 전에 원인 확인이 필요합니다.",
            related_area="validation",
            count=validation_fail,
            route="#approval",
        )
    if validation_warning:
        _attention(
            attention_items,
            severity="warning",
            title="검증 경고 항목",
            message="경고가 있는 후보는 마진과 시장 기준을 다시 확인해 주세요.",
            related_area="validation",
            count=validation_warning,
            route="#approval",
        )
    if quote_submitted + quote_reviewing:
        _attention(
            attention_items,
            severity="info",
            title="후속 확인이 필요한 견적 요청",
            message="접수 또는 검토 중인 고객 견적 요청이 있습니다.",
            related_area="quote_requests",
            count=quote_submitted + quote_reviewing,
            route="#quote-requests",
        )
    if job_failed:
        _attention(
            attention_items,
            severity="critical",
            title="실패한 워크플로 작업",
            message="최근 작업 모니터에서 실패한 작업의 입력과 오류를 확인해 주세요.",
            related_area="jobs",
            count=job_failed,
            route="#jobs",
        )
    if active_price_tables == 0:
        _attention(
            attention_items,
            severity="critical",
            title="활성 가격표 없음",
            message="활성 가격표가 없으면 견적은 원가 fallback 또는 오류로 처리될 수 있습니다.",
            related_area="price_tables",
            count=0,
            route="#price-tables",
        )
    if competitor_prices == 0:
        _attention(
            attention_items,
            severity="warning",
            title="경쟁사 참고 가격 없음",
            message="경쟁사 가격은 수동 입력 참고 데이터이며, 없으면 시장 비교 품질이 낮아집니다.",
            related_area="market_reference",
            count=0,
            route="#pricing-data",
        )
    if cost_profiles == 0:
        _attention(
            attention_items,
            severity="critical",
            title="원가 프로필 없음",
            message="원가와 최소 마진 데이터가 없으면 안전한 후보 생성이 어렵습니다.",
            related_area="cost_profiles",
            count=0,
            route="#pricing-data",
        )
    if not settings.openai_api_key:
        _attention(
            attention_items,
            severity="info",
            title="OpenAI fallback 모드",
            message="OpenAI 키가 없어 기본 설명 모드로 동작합니다. 가격 숫자는 여전히 백엔드 계산식에서만 나옵니다.",
            related_area="system_status",
            route="#system-status",
        )

    return {
        "generated_at": generated_at.isoformat(),
        "recent_window_days": RECENT_WINDOW_DAYS,
        "attention_items": attention_items,
        "approval_queue": {
            "pending_candidate_tables": pending_candidates,
            "recently_approved_candidate_tables": recently_approved_candidates,
            "recently_rejected_candidate_tables": recently_rejected_candidates,
            "active_price_tables": active_price_tables,
            "draft_price_tables": draft_price_tables,
            "human_approval_required": True,
            "automatic_activation_enabled": False,
        },
        "validation_summary": {
            "pass_count": validation_pass,
            "warning_count": validation_warning,
            "fail_count": validation_fail,
            "high_risk_count": high_risk,
            "latest_validation_at": latest_validation_at,
        },
        "data_quality": data_quality,
        "quote_request_summary": {
            "total": quote_total,
            "pending": quote_submitted,
            "reviewing": quote_reviewing,
            "quoted": quote_quoted,
            "rejected": quote_rejected,
            "archived": quote_archived,
            "recent_count": quote_recent,
        },
        "job_health": {
            "total": job_total,
            "queued": job_queued,
            "running": job_running,
            "completed": job_completed,
            "failed": job_failed,
            "cancelled": job_cancelled,
            "latest_failed_job_id": latest_failed_job["id"] if latest_failed_job else None,
            "latest_failed_job_title": latest_failed_job["title"] if latest_failed_job else None,
            "latest_failed_at": latest_failed_job["updated_at"] if latest_failed_job else None,
        },
        "audit_activity": {
            "recent_audit_log_count": recent_audit_logs,
            "recent_blocked_permission_count": recent_blocked_permissions,
            "recent_approval_event_count": recent_approval_events,
            "latest_events": latest_events,
        },
        "system_readiness": {
            "backend_health_available": True,
            "database_status_available": True,
            "openai_configured": bool(settings.openai_api_key),
            "fallback_mode_available": True,
            "audit_logging_available": True,
            "job_system_available": True,
            "database_type": _database_type(),
        },
        "notes": [
            "All dashboard insights are deterministic summaries of stored backend data.",
            "AI does not generate insight numbers, validation results, approval decisions, prices, or margins.",
            "Candidate tables remain inactive until explicit human owner approval.",
        ],
    }
