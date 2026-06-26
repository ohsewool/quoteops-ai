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


def test_quote_preview_uses_existing_cost_profile():
    response = client.post("/api/quote-preview", json={"product_id": 1, "quantity": 10})

    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == 1
    assert data["quantity"] == 10
    assert data["unit_cost"] == 2200.0
    assert data["total_cost"] == 22000.0
    assert data["target_margin_rate"] == 0.35
    assert data["suggested_unit_price"] == 3384.62
    assert data["suggested_total_price"] == 33846.15
    assert data["estimated_gross_profit"] == 11846.15
    assert data["estimated_margin_rate"] == 0.35
    assert "No AI-generated price was used." in data["calculation_notes"]


def test_quote_preview_uses_custom_override_costs():
    response = client.post(
        "/api/quote-preview",
        json={
            "product_id": 1,
            "quantity": 10,
            "material_cost": 5000,
            "labor_cost": 3000,
            "overhead_cost": 2000,
            "target_margin_rate": 0.35,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["unit_cost"] == 10000.0
    assert data["total_cost"] == 100000.0
    assert data["suggested_unit_price"] == 15384.62
    assert data["suggested_total_price"] == 153846.15
    assert data["estimated_gross_profit"] == 53846.15


def test_quote_preview_rejects_invalid_quantity():
    response = client.post("/api/quote-preview", json={"product_id": 1, "quantity": 0})

    assert response.status_code == 400


def test_quote_preview_rejects_invalid_margin_rate():
    response = client.post(
        "/api/quote-preview",
        json={"product_id": 1, "quantity": 10, "target_margin_rate": 1},
    )

    assert response.status_code == 400


def test_quote_preview_missing_product_returns_404():
    response = client.post(
        "/api/quote-preview", json={"product_id": 999999, "quantity": 10}
    )

    assert response.status_code == 404


def test_openapi_includes_quote_preview_path():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/quote-preview" in response.json()["paths"]
