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


def test_create_scenario_comparison_successfully():
    response = _create_comparison()

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Bulk order pricing comparison"
    assert data["product_id"] == 1
    assert data["product_name"] == "Demo A3 Flyer"
    assert data["competitor_context"]["reference_price_count"] == 2
    assert "No AI-generated price was used." in data["scenarios"][0]["notes"]


def test_scenario_comparison_calculates_expected_scenario_count():
    response = _create_comparison()

    assert response.status_code == 201
    assert response.json()["scenario_count"] == 3


def test_highest_margin_summary_is_correct():
    response = _create_comparison()

    assert response.status_code == 201
    assert response.json()["summary"]["highest_margin_label"] == "Premium"


def test_highest_profit_summary_is_correct():
    response = _create_comparison()

    assert response.status_code == 201
    assert response.json()["summary"]["highest_profit_label"] == "Premium"


def test_invalid_quantity_returns_error():
    response = _create_comparison(
        scenarios=[{"label": "Invalid", "quantity": 0, "margin_rate": 0.25}]
    )

    assert response.status_code == 400


def test_invalid_margin_rate_returns_error():
    response = _create_comparison(
        scenarios=[{"label": "Invalid", "quantity": 10, "margin_rate": 1}]
    )

    assert response.status_code == 400


def test_empty_scenarios_returns_error():
    response = _create_comparison(scenarios=[])

    assert response.status_code == 400


def test_missing_product_returns_404():
    response = _create_comparison(product_id=999999)

    assert response.status_code == 404


def test_missing_cost_profile_returns_404():
    db = SessionLocal()
    try:
        product = Product(
            name="Comparison Product Without Cost",
            sku=f"SCENARIO-NO-COST-{uuid4().hex[:8]}",
            category="A3 Flyer",
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        product_id = product.id
    finally:
        db.close()

    response = _create_comparison(product_id=product_id)

    assert response.status_code == 404


def test_list_scenario_comparisons_works():
    created = _create_comparison().json()
    response = client.get("/api/scenario-comparisons", headers=_auth_headers("viewer"))

    assert response.status_code == 200
    assert any(item["id"] == created["id"] for item in response.json())


def test_get_scenario_comparison_by_id_works():
    created = _create_comparison().json()
    response = client.get(
        f"/api/scenario-comparisons/{created['id']}",
        headers=_auth_headers("viewer"),
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_audit_log_is_created_after_comparison_creation():
    created = _create_comparison().json()
    response = client.get(
        "/api/audit-logs",
        params={"action": "scenario_comparison_created", "limit": 1},
        headers=_auth_headers("admin"),
    )

    assert response.status_code == 200
    log = response.json()[0]
    assert log["entity_id"] == str(created["id"])
    assert '"scenario_count":3' in log["metadata_json"]


def test_openapi_includes_scenario_comparisons_path():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/scenario-comparisons" in paths
    assert "/api/scenario-comparisons/{comparison_id}" in paths


def _create_comparison(
    *,
    product_id: int = 1,
    scenarios: list[dict] | None = None,
):
    return client.post(
        "/api/scenario-comparisons",
        headers=_auth_headers("manager"),
        json={
            "name": "Bulk order pricing comparison",
            "description": "Compare conservative, standard, and premium pricing.",
            "product_id": product_id,
            "scenarios": scenarios
            if scenarios is not None
            else [
                {"label": "Conservative", "quantity": 50, "margin_rate": 0.25},
                {"label": "Standard", "quantity": 50, "margin_rate": 0.35},
                {"label": "Premium", "quantity": 50, "margin_rate": 0.45},
            ],
            "include_competitor_context": True,
        },
    )


def _auth_headers(username: str) -> dict:
    token = _login(username, f"{username}-demo-password")
    return {"Authorization": f"Bearer {token}"}


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
