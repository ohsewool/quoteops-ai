import sys
from uuid import uuid4
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import SessionLocal, create_db_and_tables
from backend.models import Product
from backend.main import app
from backend.seed import seed_demo_data


client = TestClient(app)


def setup_module():
    create_db_and_tables()
    seed_demo_data()


def test_price_validation_passes_when_margin_meets_threshold():
    response = client.post(
        "/api/price-validation",
        json={"product_id": 1, "quantity": 10, "candidate_unit_price": 4000},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["validation_status"] == "passed"
    assert data["risk_level"] == "low"
    assert data["unit_cost"] == 2200.0
    assert data["candidate_total_price"] == 40000.0
    assert data["estimated_margin_rate"] == 0.45
    assert all(check["passed"] for check in data["checks"])
    assert "This result does not approve or activate the price." in data["calculation_notes"]


def test_price_validation_warns_when_margin_below_minimum_but_above_cost():
    response = client.post(
        "/api/price-validation",
        json={
            "product_id": 1,
            "quantity": 10,
            "candidate_unit_price": 3000,
            "minimum_margin_rate": 0.35,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["validation_status"] == "warning"
    assert data["risk_level"] == "medium"
    margin_check = _check_by_code(data["checks"], "margin_meets_minimum")
    assert margin_check["severity"] == "warning"
    assert margin_check["passed"] is False


def test_price_validation_fails_when_candidate_below_unit_cost():
    response = client.post(
        "/api/price-validation",
        json={"product_id": 1, "quantity": 10, "candidate_unit_price": 1000},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["validation_status"] == "failed"
    assert data["risk_level"] == "high"
    cost_check = _check_by_code(data["checks"], "price_above_unit_cost")
    assert cost_check["severity"] == "error"
    assert cost_check["passed"] is False


def test_price_validation_rejects_invalid_quantity():
    response = client.post(
        "/api/price-validation",
        json={"product_id": 1, "quantity": 0, "candidate_unit_price": 4000},
    )

    assert response.status_code == 400


def test_price_validation_rejects_invalid_candidate_price():
    response = client.post(
        "/api/price-validation",
        json={"product_id": 1, "quantity": 10, "candidate_unit_price": 0},
    )

    assert response.status_code == 400


def test_price_validation_missing_product_returns_404():
    response = client.post(
        "/api/price-validation",
        json={"product_id": 999999, "quantity": 10, "candidate_unit_price": 4000},
    )

    assert response.status_code == 404


def test_price_validation_missing_cost_profile_returns_404():
    db = SessionLocal()
    try:
        product = Product(
            name="Validation Test Product Without Cost",
            sku=f"VALIDATION-NO-COST-{uuid4().hex[:8]}",
            category="A3 Flyer",
            description="Temporary test product with no active cost profile.",
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        product_id = product.id
    finally:
        db.close()

    response = client.post(
        "/api/price-validation",
        json={"product_id": product_id, "quantity": 10, "candidate_unit_price": 4000},
    )

    assert response.status_code == 404


def test_price_validation_includes_competitor_context_when_requested():
    response = client.post(
        "/api/price-validation",
        json={
            "product_id": 1,
            "quantity": 10,
            "candidate_unit_price": 4000,
            "include_competitor_context": True,
        },
    )

    assert response.status_code == 200
    data = response.json()
    context = data["competitor_context"]
    assert context["available"] is True
    assert context["reference_price_count"] == 2
    assert context["average_reference_price"] == 52000.0
    assert _check_by_code(data["checks"], "competitor_reference_below_average")[
        "passed"
    ] is False


def test_openapi_includes_price_validation_path():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/price-validation" in response.json()["paths"]


def _check_by_code(checks: list[dict], code: str) -> dict:
    return next(check for check in checks if check["code"] == code)
