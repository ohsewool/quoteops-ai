import sys
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import create_db_and_tables
from backend.main import app
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
from backend.seed import seed_demo_data
from backend.services import dashboard_insights_service


client = TestClient(app)


def setup_module():
    create_db_and_tables()
    seed_demo_data()


def test_dashboard_insights_endpoint_returns_200():
    response = client.get("/api/dashboard/insights", headers=_auth_headers("viewer"))

    assert response.status_code == 200
    data = response.json()
    assert "insights" in data
    assert "Insights are generated deterministically" in data["insight_notes"][0]


def test_openapi_includes_dashboard_insights():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/dashboard/insights" in paths
    assert "/api/dashboard/insights/rules" in paths


def test_pending_approval_backlog_creates_warning_insight(monkeypatch):
    monkeypatch.setattr(
        dashboard_insights_service,
        "get_dashboard_metrics",
        lambda _db: _metrics(pending_approval_requests=1),
    )

    data = dashboard_insights_service.get_dashboard_insights(None)

    insight = _find(data.insights, "approvals", "Pending approvals need review")
    assert insight.severity == "warning"
    assert insight.metric_refs["pending_approval_requests"] == 1


def test_high_pending_approval_count_creates_critical_insight(monkeypatch):
    monkeypatch.setattr(
        dashboard_insights_service,
        "get_dashboard_metrics",
        lambda _db: _metrics(pending_approval_requests=5),
    )

    data = dashboard_insights_service.get_dashboard_insights(None)

    insight = _find(data.insights, "approvals", "Pending approvals need review")
    assert insight.severity == "critical"


def test_high_rejection_rate_creates_warning_or_critical_insight(monkeypatch):
    monkeypatch.setattr(
        dashboard_insights_service,
        "get_dashboard_metrics",
        lambda _db: _metrics(total_approval_requests=10, rejected_requests=5),
    )

    data = dashboard_insights_service.get_dashboard_insights(None)

    insight = _find(data.insights, "approvals", "Rejection rate is elevated")
    assert insight.severity == "critical"
    assert insight.metric_refs["rejection_rate"] == 0.5


def test_high_risk_validation_creates_insight(monkeypatch):
    monkeypatch.setattr(
        dashboard_insights_service,
        "get_dashboard_metrics",
        lambda _db: _metrics(high_risk_count=2),
    )

    data = dashboard_insights_service.get_dashboard_insights(None)

    insight = _find(data.insights, "validation_risk", "High risk validation results exist")
    assert insight.severity == "warning"


def test_low_average_margin_creates_insight(monkeypatch):
    monkeypatch.setattr(
        dashboard_insights_service,
        "get_dashboard_metrics",
        lambda _db: _metrics(average_estimated_margin_rate=0.14),
    )

    data = dashboard_insights_service.get_dashboard_insights(None)

    insight = _find(data.insights, "pricing_margin", "Average estimated margin is low")
    assert insight.severity == "critical"


def test_workflow_failure_creates_insight(monkeypatch):
    monkeypatch.setattr(
        dashboard_insights_service,
        "get_dashboard_metrics",
        lambda _db: _metrics(total_workflow_jobs=3, completed_jobs=1, failed_jobs=2),
    )

    data = dashboard_insights_service.get_dashboard_insights(None)

    insight = _find(data.insights, "workflow_jobs", "Workflow job failures need attention")
    assert insight.severity == "critical"
    assert insight.metric_refs["failed_jobs"] == 2


def test_healthy_metrics_create_at_least_one_info_insight(monkeypatch):
    monkeypatch.setattr(
        dashboard_insights_service,
        "get_dashboard_metrics",
        lambda _db: _metrics(recent_audit_log_count=1),
    )

    data = dashboard_insights_service.get_dashboard_insights(None)

    assert data.insight_count >= 1
    insight = _find(data.insights, "system_health", "No major pricing operation issues detected")
    assert insight.severity == "info"


def test_audit_log_is_created_after_dashboard_insights_view():
    response = client.get("/api/dashboard/insights", headers=_auth_headers("viewer"))
    assert response.status_code == 200

    logs = client.get(
        "/api/audit-logs",
        params={"action": "dashboard_insights_viewed", "limit": 1},
        headers=_auth_headers("admin"),
    )

    assert logs.status_code == 200
    assert logs.json()[0]["action"] == "dashboard_insights_viewed"
    assert "insight_count" in logs.json()[0]["metadata_json"]


def test_rules_endpoint_returns_deterministic_rules():
    response = client.get("/api/dashboard/insights/rules", headers=_auth_headers("viewer"))

    assert response.status_code == 200
    data = response.json()
    codes = {rule["code"] for rule in data["rules"]}
    assert "pending_approval_backlog" in codes
    assert "healthy_system_observation" in codes
    assert "deterministic" in data["rule_notes"][0]


def _metrics(
    *,
    total_quote_requests: int = 0,
    new_quote_requests: int = 0,
    reviewing_quote_requests: int = 0,
    total_approval_requests: int = 0,
    pending_approval_requests: int = 0,
    approved_requests: int = 0,
    rejected_requests: int = 0,
    average_estimated_margin_rate: float | None = None,
    high_risk_count: int = 0,
    total_workflow_jobs: int = 0,
    completed_jobs: int = 0,
    failed_jobs: int = 0,
    recent_audit_log_count: int = 0,
) -> DashboardResponse:
    approval_rate = (
        round(approved_requests / total_approval_requests, 4)
        if total_approval_requests
        else 0.0
    )
    rejection_rate = (
        round(rejected_requests / total_approval_requests, 4)
        if total_approval_requests
        else 0.0
    )
    job_success_rate = (
        round(completed_jobs / total_workflow_jobs, 4)
        if total_workflow_jobs
        else 0.0
    )
    return DashboardResponse(
        generated_at=datetime.utcnow(),
        summary=DashboardSummaryMetrics(
            total_products=2,
            total_quote_requests=total_quote_requests,
            total_approval_requests=total_approval_requests,
            approved_requests=approved_requests,
            rejected_requests=rejected_requests,
            pending_approval_requests=pending_approval_requests,
            average_estimated_margin_rate=average_estimated_margin_rate,
            high_risk_count=high_risk_count,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
        ),
        quote_metrics=DashboardQuoteMetrics(
            total_quote_requests=total_quote_requests,
            new_quote_requests=new_quote_requests,
            reviewing_quote_requests=reviewing_quote_requests,
            quoted_quote_requests=0,
            closed_quote_requests=0,
            cancelled_quote_requests=0,
        ),
        approval_metrics=DashboardApprovalMetrics(
            total_approval_requests=total_approval_requests,
            pending_approval_requests=pending_approval_requests,
            approved_requests=approved_requests,
            rejected_requests=rejected_requests,
            approval_rate=approval_rate,
            rejection_rate=rejection_rate,
            average_estimated_margin_rate=average_estimated_margin_rate,
        ),
        validation_metrics=DashboardValidationMetrics(
            passed_validations=0,
            warning_validations=0,
            failed_validations=0,
            low_risk_count=0,
            medium_risk_count=0,
            high_risk_count=high_risk_count,
        ),
        pricing_metrics=DashboardPricingMetrics(
            total_products=2,
            active_products=2,
            total_price_tables=0,
            draft_price_tables=0,
            active_price_tables=0,
            archived_price_tables=0,
            total_cost_profiles=2,
            average_target_margin_rate=0.35,
            average_approved_margin_rate=average_estimated_margin_rate,
        ),
        workflow_metrics=DashboardWorkflowMetrics(
            total_workflow_jobs=total_workflow_jobs,
            pending_jobs=0,
            running_jobs=0,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            cancelled_jobs=0,
            job_success_rate=job_success_rate,
        ),
        audit_metrics=DashboardAuditMetrics(
            total_audit_logs=recent_audit_log_count,
            recent_audit_log_count=recent_audit_log_count,
            top_actions=[DashboardActionCount(action="test", count=recent_audit_log_count)]
            if recent_audit_log_count
            else [],
            latest_actions=[
                DashboardLatestAction(
                    action="test",
                    actor_username="tester",
                    created_at=datetime.utcnow(),
                )
            ]
            if recent_audit_log_count
            else [],
        ),
        dashboard_notes=[],
    )


def _find(insights, category: str, title: str):
    for insight in insights:
        if insight.category == category and insight.title == title:
            return insight
    raise AssertionError(f"Insight not found: {category} / {title}")


def _auth_headers(username: str) -> dict:
    token = _login(username, f"{username}-demo-password")
    return {"Authorization": f"Bearer {token}"}


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
