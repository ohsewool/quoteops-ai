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


def test_create_workflow_job_successfully():
    response = _create_job("pricing_simulation", _pricing_simulation_input())

    assert response.status_code == 201
    data = response.json()
    assert data["job_type"] == "pricing_simulation"
    assert data["status"] == "pending"
    assert data["created_by_username"] == "manager"
    assert "No AI-generated price was used." in data["workflow_notes"]


def test_list_workflow_jobs():
    created = _create_job("pricing_simulation", _pricing_simulation_input()).json()
    response = client.get("/api/workflow-jobs", headers=_auth_headers("viewer"))

    assert response.status_code == 200
    assert any(job["id"] == created["id"] for job in response.json())


def test_get_workflow_job_by_id():
    created = _create_job("pricing_simulation", _pricing_simulation_input()).json()
    response = client.get(f"/api/workflow-jobs/{created['id']}", headers=_auth_headers("viewer"))

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_run_pending_pricing_simulation_job_successfully():
    created = _create_job("pricing_simulation", _pricing_simulation_input()).json()
    response = _run_job(created["id"])

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["result"]["scenario_count"] == 9
    assert data["result"]["product_id"] == 1


def test_run_pending_price_validation_batch_job_successfully():
    created = _create_job(
        "price_validation_batch",
        {
            "items": [
                {"product_id": 1, "quantity": 10, "candidate_unit_price": 4000},
                {"product_id": 1, "quantity": 20, "candidate_unit_price": 3000},
            ]
        },
    ).json()
    response = _run_job(created["id"])

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["result"]["item_count"] == 2
    assert data["result"]["summary"]["passed"] == 1
    assert data["result"]["summary"]["warning"] == 1


def test_run_pending_quote_request_review_job_successfully():
    quote_request = client.post(
        "/api/customer-quote-requests",
        json={
            "customer_name": "Workflow Customer",
            "customer_email": "workflow@example.com",
            "customer_company": "Workflow Co",
            "product_id": 1,
            "quantity": 10,
            "request_note": "Review by workflow job.",
        },
    ).json()
    created = _create_job(
        "quote_request_review",
        {
            "customer_quote_request_id": quote_request["id"],
            "include_quote_preview": True,
            "include_candidate_prices": True,
            "margin_rates": [0.25, 0.35],
        },
    ).json()
    response = _run_job(created["id"])

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["result"]["customer_quote_request_id"] == quote_request["id"]
    assert data["result"]["quote_preview"]["suggested_unit_price"] == 3384.62
    assert data["result"]["candidate_prices"]["candidate_count"] == 2


def test_cannot_run_already_completed_job():
    created = _create_job("pricing_simulation", _pricing_simulation_input()).json()
    assert _run_job(created["id"]).status_code == 200
    response = _run_job(created["id"])

    assert response.status_code == 400


def test_cancel_pending_job_successfully():
    created = _create_job("pricing_simulation", _pricing_simulation_input()).json()
    response = client.post(
        f"/api/workflow-jobs/{created['id']}/cancel", headers=_auth_headers("manager")
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cannot_cancel_completed_job():
    created = _create_job("pricing_simulation", _pricing_simulation_input()).json()
    assert _run_job(created["id"]).status_code == 200
    response = client.post(
        f"/api/workflow-jobs/{created['id']}/cancel", headers=_auth_headers("manager")
    )

    assert response.status_code == 400


def test_invalid_job_type_returns_error():
    response = client.post(
        "/api/workflow-jobs",
        headers=_auth_headers("manager"),
        json={"job_type": "unknown", "title": "Invalid", "input": {}},
    )

    assert response.status_code in {400, 422}


def test_missing_job_returns_404():
    response = client.get("/api/workflow-jobs/999999", headers=_auth_headers("viewer"))

    assert response.status_code == 404


def test_audit_log_is_created_after_job_creation():
    created = _create_job("pricing_simulation", _pricing_simulation_input()).json()
    response = client.get(
        "/api/audit-logs",
        params={"action": "workflow_job_created", "limit": 1},
        headers=_auth_headers("admin"),
    )

    assert response.status_code == 200
    assert response.json()[0]["entity_id"] == str(created["id"])


def test_audit_log_is_created_after_job_completion():
    created = _create_job("pricing_simulation", _pricing_simulation_input()).json()
    assert _run_job(created["id"]).status_code == 200
    response = client.get(
        "/api/audit-logs",
        params={"action": "workflow_job_completed", "limit": 1},
        headers=_auth_headers("admin"),
    )

    assert response.status_code == 200
    assert response.json()[0]["entity_id"] == str(created["id"])


def test_openapi_includes_workflow_jobs_path():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/workflow-jobs" in paths
    assert "/api/workflow-jobs/{job_id}" in paths
    assert "/api/workflow-jobs/{job_id}/run" in paths
    assert "/api/workflow-jobs/{job_id}/cancel" in paths


def _create_job(job_type: str, input_payload: dict):
    return client.post(
        "/api/workflow-jobs",
        headers=_auth_headers("manager"),
        json={
            "job_type": job_type,
            "title": "Workflow job test",
            "description": "Deterministic workflow job test.",
            "input": input_payload,
        },
    )


def _run_job(job_id: int):
    return client.post(f"/api/workflow-jobs/{job_id}/run", headers=_auth_headers("manager"))


def _pricing_simulation_input() -> dict:
    return {
        "product_id": 1,
        "quantities": [1, 10, 50],
        "margin_rates": [0.25, 0.35, 0.45],
        "include_competitor_context": True,
    }


def _auth_headers(username: str) -> dict:
    token = _login(username, f"{username}-demo-password")
    return {"Authorization": f"Bearer {token}"}


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
