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


def test_successful_login_creates_audit_log():
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin-demo-password"},
    )
    assert response.status_code == 200

    logs = _list_logs(response.json()["access_token"], action="auth_login_success")
    assert logs[0]["action"] == "auth_login_success"
    assert logs[0]["actor_username"] == "admin"
    assert logs[0]["entity_type"] == "auth"


def test_failed_login_creates_audit_log_without_password():
    sentinel_password = "do-not-log-this-password"
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": sentinel_password},
    )
    assert response.status_code == 401

    admin_token = _login("admin", "admin-demo-password")
    logs = _list_logs(admin_token, action="auth_login_failed")
    combined = str(logs[0])
    assert logs[0]["actor_username"] == "anonymous"
    assert "auth_login_failed" in combined
    assert sentinel_password not in combined
    assert "password_hash" not in combined
    assert "access_token" not in combined


def test_quote_preview_creates_audit_log():
    response = client.post("/api/quote-preview", json={"product_id": 1, "quantity": 10})
    assert response.status_code == 200

    log = _latest_log("quote_preview_created")
    assert log["entity_type"] == "quote_preview"
    assert '"product_id":1' in log["metadata_json"]
    assert '"suggested_unit_price"' in log["metadata_json"]


def test_candidate_price_generation_creates_audit_log():
    response = client.post("/api/candidate-prices", json={"product_id": 1, "quantity": 10})
    assert response.status_code == 200

    log = _latest_log("candidate_prices_generated")
    assert log["entity_type"] == "candidate_prices"
    assert '"candidate_count":3' in log["metadata_json"]


def test_validation_creates_audit_log():
    response = client.post(
        "/api/price-validation",
        json={"product_id": 1, "quantity": 10, "candidate_unit_price": 4000},
    )
    assert response.status_code == 200

    log = _latest_log("price_validation_created")
    assert log["entity_type"] == "price_validation"
    assert '"validation_status":"passed"' in log["metadata_json"]


def test_approval_request_creation_creates_audit_log():
    created = _create_approval_request()

    log = _latest_log("approval_request_created")
    assert log["entity_type"] == "approval_request"
    assert log["entity_id"] == str(created["id"])


def test_approve_and_reject_create_audit_logs():
    approve_target = _create_approval_request()
    approve_response = client.post(
        f"/api/approval-requests/{approve_target['id']}/approve",
        json={"reviewer_name": "Demo Manager", "review_note": "Approved."},
    )
    assert approve_response.status_code == 200

    reject_target = _create_approval_request()
    reject_response = client.post(
        f"/api/approval-requests/{reject_target['id']}/reject",
        json={"reviewer_name": "Demo Manager", "review_note": "Rejected."},
    )
    assert reject_response.status_code == 200

    approve_log = _latest_log("approval_request_approved")
    reject_log = _latest_log("approval_request_rejected")
    assert approve_log["entity_id"] == str(approve_target["id"])
    assert reject_log["entity_id"] == str(reject_target["id"])


def test_explanation_creation_creates_audit_log():
    response = client.post(
        "/api/explanations/quote",
        json={
            "product_id": 1,
            "quantity": 10,
            "unit_cost": 2200,
            "proposed_unit_price": 4000,
            "estimated_margin_rate": 0.45,
            "validation_status": "passed",
            "risk_level": "low",
        },
    )
    assert response.status_code == 200

    log = _latest_log("quote_explanation_created")
    assert log["entity_type"] == "explanation"
    assert '"explanation_source":"deterministic_template"' in log["metadata_json"]


def test_admin_or_manager_can_list_audit_logs():
    admin_response = client.get(
        "/api/audit-logs", headers=_auth_headers(_login("admin", "admin-demo-password"))
    )
    manager_response = client.get(
        "/api/audit-logs",
        headers=_auth_headers(_login("manager", "manager-demo-password")),
    )

    assert admin_response.status_code == 200
    assert manager_response.status_code == 200
    assert isinstance(admin_response.json(), list)


def test_viewer_is_denied_from_listing_audit_logs():
    response = client.get(
        "/api/audit-logs",
        headers=_auth_headers(_login("viewer", "viewer-demo-password")),
    )

    assert response.status_code == 403


def test_detail_endpoint_returns_one_audit_log():
    log = _latest_log("auth_login_success")
    response = client.get(
        f"/api/audit-logs/{log['id']}",
        headers=_auth_headers(_login("admin", "admin-demo-password")),
    )

    assert response.status_code == 200
    assert response.json()["id"] == log["id"]


def test_openapi_includes_audit_logs_path():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/audit-logs" in paths
    assert "/api/audit-logs/{audit_log_id}" in paths


def _latest_log(action: str) -> dict:
    admin_token = _login("admin", "admin-demo-password")
    logs = _list_logs(admin_token, action=action)
    assert logs
    return logs[0]


def _list_logs(token: str, action: str | None = None) -> list[dict]:
    params = {"limit": 100}
    if action:
        params["action"] = action
    response = client.get("/api/audit-logs", params=params, headers=_auth_headers(token))
    assert response.status_code == 200
    return response.json()


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _create_approval_request() -> dict:
    response = client.post(
        "/api/approval-requests",
        json={
            "product_id": 1,
            "quantity": 10,
            "proposed_unit_price": 4000,
            "minimum_margin_rate": 0.3,
        },
    )
    assert response.status_code == 201
    return response.json()
