import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import create_db_and_tables
from backend.main import app
from backend.seed import seed_demo_data
from backend.services.dashboard_service import _safe_rate


client = TestClient(app)


def setup_module():
    create_db_and_tables()
    seed_demo_data()


def test_dashboard_summary_endpoint_returns_200():
    response = _get_dashboard()

    assert response.status_code == 200
    assert "generated_at" in response.json()
    assert "Dashboard metrics are calculated deterministically" in response.json()["dashboard_notes"][0]


def test_dashboard_response_includes_quote_metrics():
    data = _get_dashboard().json()

    assert "quote_metrics" in data
    assert "total_quote_requests" in data["quote_metrics"]
    assert "new_quote_requests" in data["quote_metrics"]


def test_dashboard_response_includes_approval_metrics():
    data = _get_dashboard().json()

    assert "approval_metrics" in data
    assert "total_approval_requests" in data["approval_metrics"]
    assert "approval_rate" in data["approval_metrics"]


def test_dashboard_response_includes_validation_metrics():
    data = _get_dashboard().json()

    assert "validation_metrics" in data
    assert "passed_validations" in data["validation_metrics"]
    assert "high_risk_count" in data["validation_metrics"]


def test_dashboard_response_includes_pricing_metrics():
    data = _get_dashboard().json()

    assert "pricing_metrics" in data
    assert data["pricing_metrics"]["total_products"] >= 2
    assert "average_target_margin_rate" in data["pricing_metrics"]


def test_dashboard_response_includes_workflow_metrics():
    data = _get_dashboard().json()

    assert "workflow_metrics" in data
    assert "total_workflow_jobs" in data["workflow_metrics"]
    assert "job_success_rate" in data["workflow_metrics"]


def test_dashboard_response_includes_audit_metrics():
    data = _get_dashboard().json()

    assert "audit_metrics" in data
    assert "total_audit_logs" in data["audit_metrics"]
    assert "top_actions" in data["audit_metrics"]
    assert "latest_actions" in data["audit_metrics"]


def test_zero_denominator_rates_are_handled_safely():
    assert _safe_rate(0, 0) == 0.0
    assert _safe_rate(3, 0) == 0.0


def test_audit_log_is_created_after_dashboard_view():
    response = _get_dashboard()
    assert response.status_code == 200

    logs = client.get(
        "/api/audit-logs",
        params={"action": "dashboard_summary_viewed", "limit": 1},
        headers=_auth_headers("admin"),
    )

    assert logs.status_code == 200
    assert logs.json()[0]["action"] == "dashboard_summary_viewed"
    assert logs.json()[0]["entity_type"] == "dashboard"


def test_openapi_includes_dashboard_summary_path():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/dashboard/summary" in paths
    assert "/api/dashboard/metrics" in paths


def _get_dashboard():
    return client.get("/api/dashboard/summary", headers=_auth_headers("viewer"))


def _auth_headers(username: str) -> dict:
    token = _login(username, f"{username}-demo-password")
    return {"Authorization": f"Bearer {token}"}


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
