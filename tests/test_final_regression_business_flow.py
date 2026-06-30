import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import create_db_and_tables
from backend.main import app
from backend.seed import seed_demo_data


client = TestClient(app)


def setup_module():
    create_db_and_tables()
    seed_demo_data()


def test_demo_auth_roles_and_authorization_boundaries_work():
    admin = _auth_headers("admin")
    manager = _auth_headers("manager")
    viewer = _auth_headers("viewer")

    assert client.get("/api/auth/me", headers=admin).json()["role"] == "admin"
    assert client.get("/api/auth/me", headers=manager).json()["role"] == "manager"
    assert client.get("/api/auth/me", headers=viewer).json()["role"] == "viewer"
    assert client.get("/api/dashboard/summary").status_code in {401, 403}
    assert client.get("/api/dashboard/summary", headers=viewer).status_code == 200
    assert client.post("/api/demo/seed", headers=viewer).status_code in {401, 403}


def test_final_regression_core_deterministic_business_flow():
    suffix = uuid4().hex[:8]
    admin = _auth_headers("admin")
    manager = _auth_headers("manager")
    viewer = _auth_headers("viewer")

    quote = client.post("/api/quote-preview", json={"product_id": 1, "quantity": 10})
    assert quote.status_code == 200
    assert quote.json()["suggested_unit_price"] == 3384.62
    assert "No AI-generated price was used." in quote.json()["calculation_notes"]

    candidates = client.post(
        "/api/candidate-prices",
        json={
            "product_id": 1,
            "quantity": 10,
            "margin_rates": [0.25, 0.35, 0.45],
            "include_competitor_context": True,
        },
    )
    assert candidates.status_code == 200
    candidate = candidates.json()["candidates"][1]
    assert candidate["strategy"] == "target_margin"

    validation = client.post(
        "/api/price-validation",
        json={
            "product_id": 1,
            "quantity": 10,
            "candidate_unit_price": candidate["unit_price"],
            "minimum_margin_rate": 0.3,
        },
    )
    assert validation.status_code == 200
    assert validation.json()["validation_status"] == "passed"

    approval = client.post(
        "/api/approval-requests",
        json={
            "product_id": 1,
            "quantity": 10,
            "proposed_unit_price": candidate["unit_price"],
            "minimum_margin_rate": 0.3,
            "submitted_note": f"Final regression approval {suffix}",
        },
    )
    assert approval.status_code == 201
    approval_id = approval.json()["id"]
    reviewed = client.post(
        f"/api/approval-requests/{approval_id}/approve",
        json={"reviewer_name": "Final Regression", "review_note": "Human-reviewed test approval."},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "approved"

    audit = client.get(
        "/api/audit-logs",
        params={"action": "approval_request_approved", "limit": 1},
        headers=admin,
    )
    assert audit.status_code == 200
    assert audit.json()[0]["entity_id"] == str(approval_id)

    simulation = client.post(
        "/api/pricing-simulations",
        headers=manager,
        json={
            "name": f"Final regression simulation {suffix}",
            "product_id": 1,
            "quantities": [1, 10],
            "margin_rates": [0.25, 0.35],
            "include_competitor_context": True,
            "notes": "Final regression deterministic simulation.",
        },
    )
    assert simulation.status_code == 201
    assert simulation.json()["scenario_count"] == 4

    quote_request = client.post(
        "/api/customer-quote-requests",
        json={
            "customer_name": "Final Regression Customer",
            "customer_email": f"final-{suffix}@example.com",
            "customer_company": "Final Regression Co",
            "product_id": 1,
            "quantity": 25,
            "request_note": "Final regression customer request.",
        },
    )
    assert quote_request.status_code == 201

    comparison = client.post(
        "/api/scenario-comparisons",
        headers=manager,
        json={
            "name": f"Final regression scenario comparison {suffix}",
            "product_id": 1,
            "scenarios": [
                {"label": "Conservative", "quantity": 50, "margin_rate": 0.25},
                {"label": "Premium", "quantity": 50, "margin_rate": 0.45},
            ],
            "include_competitor_context": True,
        },
    )
    assert comparison.status_code == 201
    assert comparison.json()["summary"]["highest_margin_label"] == "Premium"

    dashboard = client.get("/api/dashboard/summary", headers=viewer)
    insights = client.get("/api/dashboard/insights", headers=viewer)
    assert dashboard.status_code == 200
    assert insights.status_code == 200
    assert "insights" in insights.json()

    report = client.post(
        "/api/html-reports",
        headers=manager,
        json={"report_type": "dashboard_summary", "title": f"Final regression report {suffix}"},
    )
    assert report.status_code == 201
    content = client.get(f"/api/html-reports/{report.json()['id']}/content", headers=viewer)
    assert content.status_code == 200
    assert content.text.startswith("<!doctype html>")

    demo_status = client.get("/api/demo/status", headers=viewer)
    demo_guide = client.get("/api/demo/guide", headers=viewer)
    assert demo_status.status_code == 200
    assert demo_guide.status_code == 200
    assert "Demo tools do not approve, reject, or activate production prices." in demo_guide.text


def _auth_headers(username: str) -> dict:
    token = _login(username, f"{username}-demo-password")
    return {"Authorization": f"Bearer {token}"}


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
