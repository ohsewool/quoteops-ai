import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import create_db_and_tables
from backend.main import app
from backend.seed import seed_demo_data


client = TestClient(app)


def setup_module():
    create_db_and_tables()
    seed_demo_data()


def test_create_dashboard_summary_html_report_successfully():
    response = _create_report("dashboard_summary", "Current KPI dashboard report")

    assert response.status_code == 201
    data = response.json()
    assert data["report_type"] == "dashboard_summary"
    assert data["source_id"] is None
    assert "deterministic" in data["summary_text"]


def test_create_approval_request_html_report_successfully():
    approval = _create_approval_request()
    response = _create_report(
        "approval_request",
        "Approval request report",
        source_id=approval["id"],
    )

    assert response.status_code == 201
    assert response.json()["source_id"] == str(approval["id"])


def test_create_pricing_simulation_html_report_successfully():
    simulation = _create_pricing_simulation()
    response = _create_report(
        "pricing_simulation",
        "Pricing simulation report",
        source_id=simulation["id"],
    )

    assert response.status_code == 201
    assert response.json()["report_type"] == "pricing_simulation"


def test_create_scenario_comparison_html_report_successfully():
    comparison = _create_scenario_comparison()
    response = _create_report(
        "scenario_comparison",
        "Scenario comparison report",
        source_id=comparison["id"],
    )

    assert response.status_code == 201
    assert response.json()["report_type"] == "scenario_comparison"


def test_list_html_reports():
    created = _create_report("dashboard_summary", "Listable dashboard report").json()
    response = client.get("/api/html-reports", headers=_auth_headers("viewer"))

    assert response.status_code == 200
    assert any(report["id"] == created["id"] for report in response.json())


def test_get_html_report_by_id():
    created = _create_report("dashboard_summary", "Get dashboard report").json()
    response = client.get(
        f"/api/html-reports/{created['id']}",
        headers=_auth_headers("viewer"),
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_html_report_content_returns_html():
    created = _create_report("dashboard_summary", "Content dashboard report").json()
    response = client.get(
        f"/api/html-reports/{created['id']}/content",
        headers=_auth_headers("viewer"),
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text.startswith("<!doctype html>")


def test_missing_source_returns_404_where_source_id_required():
    response = _create_report(
        "approval_request",
        "Missing approval report",
        source_id=999999,
    )

    assert response.status_code == 404


def test_invalid_report_type_returns_400():
    response = _create_report("not_supported", "Invalid report")

    assert response.status_code == 400


def test_html_content_includes_decision_boundary_text():
    created = _create_report("dashboard_summary", "Boundary dashboard report").json()
    response = client.get(
        f"/api/html-reports/{created['id']}/content",
        headers=_auth_headers("viewer"),
    )

    assert response.status_code == 200
    assert "Decision boundary" in response.text
    assert "does not approve" in response.text


def test_html_content_does_not_include_password_token_or_secret_fields():
    created = _create_report("dashboard_summary", "Security dashboard report").json()
    response = client.get(
        f"/api/html-reports/{created['id']}/content",
        headers=_auth_headers("viewer"),
    )

    lowered = response.text.lower()
    assert "password" not in lowered
    assert "token" not in lowered
    assert "secret" not in lowered


def test_audit_log_is_created_after_report_creation():
    created = _create_report("dashboard_summary", "Audited dashboard report").json()
    response = client.get(
        "/api/audit-logs",
        params={"action": "html_report_created", "limit": 1},
        headers=_auth_headers("admin"),
    )

    assert response.status_code == 200
    log = response.json()[0]
    assert log["entity_id"] == str(created["id"])
    assert "html_content" not in log["metadata_json"]


def test_openapi_includes_html_reports_path():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/html-reports" in paths
    assert "/api/html-reports/{report_id}" in paths
    assert "/api/html-reports/{report_id}/content" in paths


def _create_report(report_type: str, title: str, source_id: int | None = None):
    payload = {"report_type": report_type, "title": title}
    if source_id is not None:
        payload["source_id"] = source_id
    return client.post("/api/html-reports", headers=_auth_headers("manager"), json=payload)


def _create_approval_request() -> dict:
    response = client.post(
        "/api/approval-requests",
        json={
            "product_id": 1,
            "quantity": 10,
            "proposed_unit_price": 4000,
            "minimum_margin_rate": 0.3,
            "submitted_note": "Report test approval snapshot.",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_pricing_simulation() -> dict:
    response = client.post(
        "/api/pricing-simulations",
        headers=_auth_headers("manager"),
        json={
            "name": "Report simulation",
            "product_id": 1,
            "quantities": [1, 10],
            "margin_rates": [0.25, 0.35],
            "include_competitor_context": False,
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_scenario_comparison() -> dict:
    response = client.post(
        "/api/scenario-comparisons",
        headers=_auth_headers("manager"),
        json={
            "name": "Report scenario comparison",
            "product_id": 1,
            "scenarios": [
                {"label": "Conservative", "quantity": 50, "margin_rate": 0.25},
                {"label": "Premium", "quantity": 50, "margin_rate": 0.45},
            ],
            "include_competitor_context": False,
        },
    )
    assert response.status_code == 201
    return response.json()


def _auth_headers(username: str) -> dict:
    token = _login(username, f"{username}-demo-password")
    return {"Authorization": f"Bearer {token}"}


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
