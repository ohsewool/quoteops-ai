from datetime import datetime

from sqlalchemy.orm import Session

from backend.schemas import (
    DashboardInsight,
    DashboardInsightRule,
    DashboardInsightRulesResponse,
    DashboardInsightsResponse,
)
from backend.services.dashboard_service import get_dashboard_metrics


INSIGHT_NOTES = [
    "Insights are generated deterministically from stored KPI metrics.",
    "No AI-generated price, approval, or validation decision was used.",
    "Insights are advisory and require human review.",
]
RULE_NOTES = [
    "Dashboard insight rules are deterministic.",
    "Rules only explain existing KPI metrics and do not modify pricing data.",
    "No external AI, scraping, email, approval, rejection, or activation is performed.",
]


def get_dashboard_insights(db: Session) -> DashboardInsightsResponse:
    metrics = get_dashboard_metrics(db)
    insights: list[DashboardInsight] = []

    pending = metrics.approval_metrics.pending_approval_requests
    if pending > 0:
        insights.append(
            DashboardInsight(
                category="approvals",
                severity="critical" if pending >= 5 else "warning",
                title="Pending approvals need review",
                message=(
                    f"There are {pending} pending approval requests. Review pending "
                    "quotes before they delay customer responses."
                ),
                metric_refs={"pending_approval_requests": pending},
                recommended_action="Open the approval request list and review pending items.",
                decision_boundary="This insight does not approve or reject any price.",
            )
        )

    rejection_rate = metrics.approval_metrics.rejection_rate
    if rejection_rate >= 0.3:
        insights.append(
            DashboardInsight(
                category="approvals",
                severity="critical" if rejection_rate >= 0.5 else "warning",
                title="Rejection rate is elevated",
                message=(
                    f"The approval rejection rate is {rejection_rate:.0%}. Review recent "
                    "rejections for pricing policy or margin issues."
                ),
                metric_refs={"rejection_rate": rejection_rate},
                recommended_action="Review rejected approval requests and update guidance if needed.",
                decision_boundary="This insight does not change approval request status.",
            )
        )

    high_risk_count = metrics.validation_metrics.high_risk_count
    if high_risk_count > 0:
        insights.append(
            DashboardInsight(
                category="validation_risk",
                severity="critical" if high_risk_count >= 5 else "warning",
                title="High risk validation results exist",
                message=(
                    f"There are {high_risk_count} high risk validation results. Inspect "
                    "the related quotes before customer-facing use."
                ),
                metric_refs={"high_risk_count": high_risk_count},
                recommended_action="Review high risk validation checks and adjust candidate prices manually.",
                decision_boundary="This insight does not validate, approve, or activate any price.",
            )
        )

    average_margin = metrics.approval_metrics.average_estimated_margin_rate
    if average_margin is not None and average_margin < 0.25:
        insights.append(
            DashboardInsight(
                category="pricing_margin",
                severity="critical" if average_margin < 0.15 else "warning",
                title="Average estimated margin is low",
                message=(
                    f"The average estimated approval margin is {average_margin:.0%}. "
                    "Margin protection may need attention."
                ),
                metric_refs={"average_estimated_margin_rate": average_margin},
                recommended_action="Review cost profiles and minimum margin assumptions.",
                decision_boundary="This insight does not generate or change prices.",
            )
        )

    failed_jobs = metrics.workflow_metrics.failed_jobs
    if failed_jobs > 0:
        success_rate = metrics.workflow_metrics.job_success_rate
        insights.append(
            DashboardInsight(
                category="workflow_jobs",
                severity="critical" if success_rate < 0.8 else "warning",
                title="Workflow job failures need attention",
                message=(
                    f"There are {failed_jobs} failed workflow jobs and the current job "
                    f"success rate is {success_rate:.0%}."
                ),
                metric_refs={"failed_jobs": failed_jobs, "job_success_rate": success_rate},
                recommended_action="Open workflow jobs and inspect failed job error messages.",
                decision_boundary="This insight does not rerun, cancel, or modify workflow jobs.",
            )
        )

    quote_backlog = (
        metrics.quote_metrics.new_quote_requests
        + metrics.quote_metrics.reviewing_quote_requests
    )
    if quote_backlog > 0:
        insights.append(
            DashboardInsight(
                category="quote_requests",
                severity="warning" if quote_backlog >= 10 else "info",
                title="Quote request backlog is open",
                message=(
                    f"There are {quote_backlog} new or reviewing quote requests. Keep "
                    "customer responses moving."
                ),
                metric_refs={
                    "new_quote_requests": metrics.quote_metrics.new_quote_requests,
                    "reviewing_quote_requests": metrics.quote_metrics.reviewing_quote_requests,
                    "quote_request_backlog": quote_backlog,
                },
                recommended_action="Review new and reviewing customer quote requests.",
                decision_boundary="This insight does not create or send quotes.",
            )
        )

    recent_audit_count = metrics.audit_metrics.recent_audit_log_count
    if recent_audit_count == 0:
        insights.append(
            DashboardInsight(
                category="audit_activity",
                severity="info",
                title="No recent audit activity",
                message="No audit log activity was recorded in the recent audit window.",
                metric_refs={"recent_audit_log_count": recent_audit_count},
                recommended_action="Confirm whether the system has been used recently.",
                decision_boundary="This insight does not create audit records by itself.",
            )
        )

    if not any(insight.severity in {"warning", "critical"} for insight in insights):
        insights.append(
            DashboardInsight(
                category="system_health",
                severity="info",
                title="No major pricing operation issues detected",
                message=(
                    "Current dashboard metrics do not show approval, validation, margin, "
                    "workflow, or quote backlog issues that require immediate action."
                ),
                metric_refs={
                    "pending_approval_requests": pending,
                    "high_risk_count": high_risk_count,
                    "failed_jobs": failed_jobs,
                    "quote_request_backlog": quote_backlog,
                },
                recommended_action="Continue normal monitoring and human review.",
                decision_boundary="This insight is advisory and does not change system state.",
            )
        )

    return DashboardInsightsResponse(
        generated_at=datetime.utcnow(),
        insight_count=len(insights),
        insights=insights,
        insight_notes=INSIGHT_NOTES,
    )


def get_dashboard_insight_rules() -> DashboardInsightRulesResponse:
    return DashboardInsightRulesResponse(
        rules=[
            DashboardInsightRule(
                code="pending_approval_backlog",
                category="approvals",
                metric="pending_approval_requests",
                warning_threshold="> 0",
                critical_threshold=">= 5",
                description="Warn when human approval requests are waiting.",
            ),
            DashboardInsightRule(
                code="rejection_rate_warning",
                category="approvals",
                metric="rejection_rate",
                warning_threshold=">= 0.3",
                critical_threshold=">= 0.5",
                description="Warn when rejected approval decisions become frequent.",
            ),
            DashboardInsightRule(
                code="high_risk_validation_warning",
                category="validation_risk",
                metric="high_risk_count",
                warning_threshold="> 0",
                critical_threshold=">= 5",
                description="Warn when stored validation snapshots include high risk items.",
            ),
            DashboardInsightRule(
                code="low_average_margin_warning",
                category="pricing_margin",
                metric="average_estimated_margin_rate",
                warning_threshold="< 0.25",
                critical_threshold="< 0.15",
                description="Warn when stored approval margins are below target thresholds.",
            ),
            DashboardInsightRule(
                code="workflow_job_failure_warning",
                category="workflow_jobs",
                metric="failed_jobs",
                warning_threshold="> 0",
                critical_threshold="job_success_rate < 0.8",
                description="Warn when deterministic workflow jobs fail.",
            ),
            DashboardInsightRule(
                code="quote_request_backlog",
                category="quote_requests",
                metric="new_quote_requests + reviewing_quote_requests",
                warning_threshold=">= 10",
                critical_threshold=None,
                description="Show open customer quote request backlog.",
            ),
            DashboardInsightRule(
                code="audit_activity_observation",
                category="audit_activity",
                metric="recent_audit_log_count",
                warning_threshold=None,
                critical_threshold=None,
                description="Show an info observation when no recent audit activity exists.",
            ),
            DashboardInsightRule(
                code="healthy_system_observation",
                category="system_health",
                metric="warning_or_critical_insight_count",
                warning_threshold=None,
                critical_threshold=None,
                description="Show a healthy info card when no warning or critical insights exist.",
            ),
        ],
        rule_notes=RULE_NOTES,
    )
