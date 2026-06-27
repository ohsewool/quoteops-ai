from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import (
    AuditLog,
    CostProfile,
    CustomerQuoteRequest,
    PriceApprovalRequest,
    PriceTable,
    Product,
    WorkflowJob,
)
from backend.schemas import (
    DashboardActionCount,
    DashboardApprovalMetrics,
    DashboardAuditMetrics,
    DashboardLatestAction,
    DashboardPricingMetrics,
    DashboardQuoteMetrics,
    DashboardResponse,
    DashboardSummaryMetrics,
    DashboardValidationMetrics,
    DashboardWorkflowMetrics,
)


DASHBOARD_NOTES = [
    "Dashboard metrics are calculated deterministically from stored system data.",
    "No AI-generated insights are included in this response.",
    "Metrics do not approve, reject, or activate prices.",
    "Validation metrics are derived from stored approval request snapshot fields.",
]


def get_dashboard_metrics(db: Session) -> DashboardResponse:
    quote_metrics = get_quote_metrics(db)
    approval_metrics = get_approval_metrics(db)
    validation_metrics = get_validation_metrics(db)
    pricing_metrics = get_pricing_metrics(db)
    workflow_metrics = get_workflow_metrics(db)
    audit_metrics = get_audit_metrics(db)

    return DashboardResponse(
        generated_at=datetime.utcnow(),
        summary=DashboardSummaryMetrics(
            total_products=pricing_metrics.total_products,
            total_quote_requests=quote_metrics.total_quote_requests,
            total_approval_requests=approval_metrics.total_approval_requests,
            approved_requests=approval_metrics.approved_requests,
            rejected_requests=approval_metrics.rejected_requests,
            pending_approval_requests=approval_metrics.pending_approval_requests,
            average_estimated_margin_rate=approval_metrics.average_estimated_margin_rate,
            high_risk_count=validation_metrics.high_risk_count,
            completed_jobs=workflow_metrics.completed_jobs,
            failed_jobs=workflow_metrics.failed_jobs,
        ),
        quote_metrics=quote_metrics,
        approval_metrics=approval_metrics,
        validation_metrics=validation_metrics,
        pricing_metrics=pricing_metrics,
        workflow_metrics=workflow_metrics,
        audit_metrics=audit_metrics,
        dashboard_notes=DASHBOARD_NOTES,
    )


def get_quote_metrics(db: Session) -> DashboardQuoteMetrics:
    status_counts = _count_by_value(db, CustomerQuoteRequest.status)
    total = sum(status_counts.values())
    return DashboardQuoteMetrics(
        total_quote_requests=total,
        new_quote_requests=status_counts.get("new", 0),
        reviewing_quote_requests=status_counts.get("reviewing", 0),
        quoted_quote_requests=status_counts.get("quoted", 0),
        closed_quote_requests=status_counts.get("closed", 0),
        cancelled_quote_requests=status_counts.get("cancelled", 0),
    )


def get_approval_metrics(db: Session) -> DashboardApprovalMetrics:
    status_counts = _count_by_value(db, PriceApprovalRequest.status)
    total = sum(status_counts.values())
    approved = status_counts.get("approved", 0)
    rejected = status_counts.get("rejected", 0)
    average_margin = _average(db, PriceApprovalRequest.estimated_margin_rate)
    return DashboardApprovalMetrics(
        total_approval_requests=total,
        pending_approval_requests=status_counts.get("pending", 0),
        approved_requests=approved,
        rejected_requests=rejected,
        approval_rate=_safe_rate(approved, total),
        rejection_rate=_safe_rate(rejected, total),
        average_estimated_margin_rate=average_margin,
    )


def get_validation_metrics(db: Session) -> DashboardValidationMetrics:
    validation_counts = _count_by_value(db, PriceApprovalRequest.validation_status)
    risk_counts = _count_by_value(db, PriceApprovalRequest.risk_level)
    return DashboardValidationMetrics(
        passed_validations=validation_counts.get("passed", 0),
        warning_validations=validation_counts.get("warning", 0),
        failed_validations=validation_counts.get("failed", 0),
        low_risk_count=risk_counts.get("low", 0),
        medium_risk_count=risk_counts.get("medium", 0),
        high_risk_count=risk_counts.get("high", 0),
    )


def get_pricing_metrics(db: Session) -> DashboardPricingMetrics:
    table_status_counts = _count_by_value(db, PriceTable.status)
    approved_margin = _average_filtered(
        db,
        PriceApprovalRequest.estimated_margin_rate,
        PriceApprovalRequest.status == "approved",
    )
    return DashboardPricingMetrics(
        total_products=db.query(Product).count(),
        active_products=db.query(Product).filter(Product.active.is_(True)).count(),
        total_price_tables=sum(table_status_counts.values()),
        draft_price_tables=table_status_counts.get("draft", 0),
        active_price_tables=table_status_counts.get("active", 0),
        archived_price_tables=table_status_counts.get("archived", 0),
        total_cost_profiles=db.query(CostProfile).count(),
        average_target_margin_rate=_average(db, CostProfile.target_margin_rate),
        average_approved_margin_rate=approved_margin,
    )


def get_workflow_metrics(db: Session) -> DashboardWorkflowMetrics:
    status_counts = _count_by_value(db, WorkflowJob.status)
    total = sum(status_counts.values())
    completed = status_counts.get("completed", 0)
    return DashboardWorkflowMetrics(
        total_workflow_jobs=total,
        pending_jobs=status_counts.get("pending", 0),
        running_jobs=status_counts.get("running", 0),
        completed_jobs=completed,
        failed_jobs=status_counts.get("failed", 0),
        cancelled_jobs=status_counts.get("cancelled", 0),
        job_success_rate=_safe_rate(completed, total),
    )


def get_audit_metrics(db: Session) -> DashboardAuditMetrics:
    recent_cutoff = datetime.utcnow() - timedelta(days=7)
    top_actions = [
        DashboardActionCount(action=action, count=count)
        for action, count in (
            db.query(AuditLog.action, func.count(AuditLog.id))
            .group_by(AuditLog.action)
            .order_by(func.count(AuditLog.id).desc(), AuditLog.action)
            .limit(5)
            .all()
        )
    ]
    latest_actions = [
        DashboardLatestAction(
            action=log.action,
            actor_username=log.actor_username,
            created_at=log.created_at,
        )
        for log in db.query(AuditLog)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(5)
        .all()
    ]
    return DashboardAuditMetrics(
        total_audit_logs=db.query(AuditLog).count(),
        recent_audit_log_count=(
            db.query(AuditLog).filter(AuditLog.created_at >= recent_cutoff).count()
        ),
        top_actions=top_actions,
        latest_actions=latest_actions,
    )


def _count_by_value(db: Session, column) -> dict[str, int]:
    return {
        str(value): int(count)
        for value, count in db.query(column, func.count()).group_by(column).all()
        if value is not None
    }


def _average(db: Session, column) -> float | None:
    return _round_optional(db.query(func.avg(column)).scalar())


def _average_filtered(db: Session, column, condition) -> float | None:
    return _round_optional(db.query(func.avg(column)).filter(condition).scalar())


def _round_optional(value: float | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 4)


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 4)
