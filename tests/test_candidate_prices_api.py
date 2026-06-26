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


def test_candidate_prices_generate_default_margins():
    response = client.post("/api/candidate-prices", json={"product_id": 1, "quantity": 10})

    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == 1
    assert data["quantity"] == 10
    assert data["unit_cost"] == 2200.0
    assert data["total_cost"] == 22000.0
    assert [item["strategy"] for item in data["candidates"]] == [
        "low_margin",
        "target_margin",
        "premium_margin",
    ]
    assert [item["margin_rate"] for item in data["candidates"]] == [0.25, 0.35, 0.45]
    assert data["candidates"][0]["unit_price"] == 2933.33
    assert data["candidates"][1]["unit_price"] == 3384.62
    assert data["candidates"][2]["unit_price"] == 4000.0
    assert data["competitor_context"] is None
    assert "No AI-generated price was used." in data["calculation_notes"]


def test_candidate_prices_generate_custom_margins():
    response = client.post(
        "/api/candidate-prices",
        json={"product_id": 1, "quantity": 10, "margin_rates": [0.2, 0.4]},
    )

    assert response.status_code == 200
    data = response.json()
    assert [item["strategy"] for item in data["candidates"]] == [
        "custom_margin_1",
        "custom_margin_2",
    ]
    assert [item["margin_rate"] for item in data["candidates"]] == [0.2, 0.4]
    assert data["candidates"][0]["unit_price"] == 2750.0
    assert data["candidates"][1]["unit_price"] == 3666.67


def test_candidate_prices_reject_invalid_quantity():
    response = client.post("/api/candidate-prices", json={"product_id": 1, "quantity": 0})

    assert response.status_code == 400


def test_candidate_prices_reject_invalid_margin_rate():
    response = client.post(
        "/api/candidate-prices",
        json={"product_id": 1, "quantity": 10, "margin_rates": [0.25, 1]},
    )

    assert response.status_code == 400


def test_candidate_prices_missing_product_returns_404():
    response = client.post(
        "/api/candidate-prices", json={"product_id": 999999, "quantity": 10}
    )

    assert response.status_code == 404


def test_candidate_prices_include_competitor_context_when_requested():
    response = client.post(
        "/api/candidate-prices",
        json={
            "product_id": 1,
            "quantity": 10,
            "include_competitor_context": True,
        },
    )

    assert response.status_code == 200
    context = response.json()["competitor_context"]
    assert context["available"] is True
    assert context["reference_price_count"] == 2
    assert context["min_reference_price"] == 52000.0
    assert context["max_reference_price"] == 52000.0
    assert context["average_reference_price"] == 52000.0


def test_openapi_includes_candidate_prices_path():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/candidate-prices" in response.json()["paths"]
