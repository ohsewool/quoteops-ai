import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import SessionLocal, create_db_and_tables
from backend.main import app
from backend.models import Product
from backend.seed import seed_demo_data


client = TestClient(app)


def setup_module():
    create_db_and_tables()
    seed_demo_data()


def test_create_pricing_simulation_successfully():
    response = _create_simulation()

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Demo simulation for bulk order"
    assert data["product_id"] == 1
    assert data["product_name"] == "Demo A3 Flyer"
    assert data["unit_cost"] == 2200.0
    assert data["include_competitor_context"] is True
    assert data["competitor_context"]["reference_price_count"] == 2
    assert "No AI-generated price was used." in data["simulation_notes"]


def test_simulation_creates_expected_scenario_count():
    response = _create_simulation(quantities=[1, 10, 50], margin_rates=[0.25, 0.35, 0.45])

    assert response.status_code == 201
    data = response.json()
    assert data["scenario_count"] == 9
    sample = next(
        scenario
        for scenario in data["scenarios"]
        if scenario["quantity"] == 10 and scenario["margin_rate"] == 0.35
    )
    assert sample["unit_price"] == 3384.62
    assert sample["total_price"] == 33846.15
    assert sample["total_cost"] == 22000.0
    assert sample["estimated_gross_profit"] == 11846.15
    assert sample["estimated_margin_rate"] == 0.35
    assert sample["validation_status"] == "passed"
    assert sample["risk_level"] == "low"


def test_invalid_quantity_returns_error():
    response = _create_simulation(quantities=[1, 0], margin_rates=[0.35])

    assert response.status_code == 400


def test_invalid_margin_rate_returns_error():
    response = _create_simulation(quantities=[1], margin_rates=[0.35, 1])

    assert response.status_code == 400


def test_missing_product_returns_404():
    response = _create_simulation(product_id=999999)

    assert response.status_code == 404


def test_missing_cost_profile_returns_404():
    db = SessionLocal()
    try:
        product = Product(
            name="Simulation Product Without Cost",
            sku=f"SIM-NO-COST-{uuid4().hex[:8]}",
            category="A3 Flyer",
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        product_id = product.id
    finally:
        db.close()

    response = _create_simulation(product_id=product_id)

    assert response.status_code == 404


def test_scenario_count_limit_works():
    response = _create_simulation(
        quantities=list(range(1, 12)),
        margin_rates=[0.01 * index for index in range(10)],
    )

    assert response.status_code == 400


def test_list_simulations_works():
    created = _create_simulation().json()
    response = client.get("/api/pricing-simulations", headers=_auth_headers("viewer"))

    assert response.status_code == 200
    assert any(item["id"] == created["id"] for item in response.json())


def test_get_simulation_by_id_works():
    created = _create_simulation().json()
    response = client.get(
        f"/api/pricing-simulations/{created['id']}",
        headers=_auth_headers("viewer"),
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_audit_log_is_created_after_simulation():
    created = _create_simulation().json()
    response = client.get(
        "/api/audit-logs",
        params={"action": "pricing_simulation_created", "limit": 1},
        headers=_auth_headers("admin"),
    )

    assert response.status_code == 200
    log = response.json()[0]
    assert log["entity_id"] == str(created["id"])
    assert '"scenario_count":9' in log["metadata_json"]


def test_openapi_includes_pricing_simulations_path():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/pricing-simulations" in paths
    assert "/api/pricing-simulations/{simulation_id}" in paths


def _create_simulation(
    *,
    product_id: int = 1,
    quantities: list[int] | None = None,
    margin_rates: list[float] | None = None,
):
    return client.post(
        "/api/pricing-simulations",
        headers=_auth_headers("manager"),
        json={
            "name": "Demo simulation for bulk order",
            "product_id": product_id,
            "quantities": quantities or [1, 10, 50],
            "margin_rates": margin_rates or [0.25, 0.35, 0.45],
            "include_competitor_context": True,
            "notes": "Compare small and bulk order scenarios.",
        },
    )


def _auth_headers(username: str) -> dict:
    token = _login(username, f"{username}-demo-password")
    return {"Authorization": f"Bearer {token}"}


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
