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


def test_create_approval_request_successfully():
    data = _create_request().json()

    assert data["product_id"] == 1
    assert data["status"] == "pending"
    assert data["proposed_unit_price"] == 4000.0
    assert data["proposed_total_price"] == 40000.0
    assert data["validation_status"] == "passed"
    assert data["risk_level"] == "low"
    assert data["reviewer_name"] is None
    assert data["reviewed_at"] is None
    assert "No AI approval decision was used." in data["workflow_notes"]


def test_list_approval_requests():
    created = _create_request().json()
    response = client.get("/api/approval-requests")

    assert response.status_code == 200
    assert any(item["id"] == created["id"] for item in response.json())


def test_get_approval_request_by_id():
    created = _create_request().json()
    response = client.get(f"/api/approval-requests/{created['id']}")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_approve_pending_request_successfully():
    created = _create_request().json()
    response = client.post(
        f"/api/approval-requests/{created['id']}/approve",
        json={
            "reviewer_name": "Demo Manager",
            "review_note": "Approved for customer quote.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["reviewer_name"] == "Demo Manager"
    assert data["review_note"] == "Approved for customer quote."
    assert data["reviewed_at"] is not None


def test_reject_pending_request_successfully():
    created = _create_request().json()
    response = client.post(
        f"/api/approval-requests/{created['id']}/reject",
        json={
            "reviewer_name": "Demo Manager",
            "review_note": "Rejected because margin is too low.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["reviewer_name"] == "Demo Manager"
    assert data["review_note"] == "Rejected because margin is too low."
    assert data["reviewed_at"] is not None


def test_cannot_approve_already_approved_request():
    created = _create_request().json()
    decision = {"reviewer_name": "Demo Manager", "review_note": "Approved."}
    first_response = client.post(
        f"/api/approval-requests/{created['id']}/approve", json=decision
    )
    second_response = client.post(
        f"/api/approval-requests/{created['id']}/approve", json=decision
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 400


def test_cannot_reject_already_rejected_request():
    created = _create_request().json()
    decision = {"reviewer_name": "Demo Manager", "review_note": "Rejected."}
    first_response = client.post(
        f"/api/approval-requests/{created['id']}/reject", json=decision
    )
    second_response = client.post(
        f"/api/approval-requests/{created['id']}/reject", json=decision
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 400


def test_approval_request_rejects_invalid_quantity():
    response = client.post(
        "/api/approval-requests",
        json={"product_id": 1, "quantity": 0, "proposed_unit_price": 4000},
    )

    assert response.status_code == 400


def test_approval_request_rejects_invalid_proposed_price():
    response = client.post(
        "/api/approval-requests",
        json={"product_id": 1, "quantity": 10, "proposed_unit_price": 0},
    )

    assert response.status_code == 400


def test_approval_request_missing_product_returns_404():
    response = client.post(
        "/api/approval-requests",
        json={"product_id": 999999, "quantity": 10, "proposed_unit_price": 4000},
    )

    assert response.status_code == 404


def test_openapi_includes_approval_request_endpoints():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/approval-requests" in paths
    assert "/api/approval-requests/{approval_request_id}" in paths
    assert "/api/approval-requests/{approval_request_id}/approve" in paths
    assert "/api/approval-requests/{approval_request_id}/reject" in paths


def _create_request():
    response = client.post(
        "/api/approval-requests",
        json={
            "product_id": 1,
            "quantity": 10,
            "proposed_unit_price": 4000,
            "minimum_margin_rate": 0.3,
            "submitted_note": "Customer requested quote for 10 units.",
        },
    )
    assert response.status_code == 201
    return response
