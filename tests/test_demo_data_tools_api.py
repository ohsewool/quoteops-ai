import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import create_db_and_tables
from backend.main import app
from backend.models import Product
from backend.seed import seed_demo_data


client = TestClient(app)


def setup_module():
    create_db_and_tables()
    seed_demo_data()


def test_demo_status_endpoint_returns_counts():
    response = client.get("/api/demo/status", headers=_auth_headers("viewer"))

    assert response.status_code == 200
    data = response.json()
    assert "products" in data["counts"]
    assert data["demo_notes"]


def test_demo_seed_endpoint_creates_deterministic_demo_data():
    response = client.post("/api/demo/seed", headers=_auth_headers("admin"))

    assert response.status_code == 201
    data = response.json()
    assert data["seed_completed"] is True
    assert data["created_or_verified"]["products"] >= 5

    product_response = client.get("/api/products", headers=_auth_headers("viewer"))
    assert product_response.status_code == 200
    skus = {product["sku"] for product in product_response.json()}
    assert "DEMO-BANNER-001" in skus
    assert "DEMO-STICKER-001" in skus


def test_demo_seed_is_idempotent():
    first = client.post("/api/demo/seed", headers=_auth_headers("admin")).json()
    second = client.post("/api/demo/seed", headers=_auth_headers("admin")).json()

    assert second["created_or_verified"]["products"] == first["created_or_verified"]["products"]
    assert (
        second["created_or_verified"]["scenario_comparisons"]
        == first["created_or_verified"]["scenario_comparisons"]
    )


def test_demo_full_scenario_endpoint_returns_presentation_steps():
    response = client.post("/api/demo/scenario/full", headers=_auth_headers("manager"))

    assert response.status_code == 201
    data = response.json()
    assert data["ready"] is True
    assert data["demo_product_sku"] == "DEMO-BANNER-001"
    assert len(data["steps"]) >= 5
    assert "No AI-generated price was used." in data["decision_boundaries"]


def test_demo_guide_endpoint_returns_safe_demo_instructions():
    response = client.get("/api/demo/guide", headers=_auth_headers("viewer"))

    assert response.status_code == 200
    data = response.json()
    assert data["demo_login_users"]
    assert data["recommended_demo_flow"]
    assert "Do not claim AI generated the numeric prices." in data["what_not_to_claim"]


def test_demo_guide_does_not_expose_password_hashes():
    response = client.get("/api/demo/guide", headers=_auth_headers("viewer"))

    lowered = response.text.lower()
    assert "password_hash" not in lowered
    assert "access_token" not in lowered
    assert "auth_secret" not in lowered
    assert "database_url" not in lowered


def test_demo_reset_only_targets_known_demo_records_or_reports_safety():
    client.post("/api/demo/seed", headers=_auth_headers("admin"))
    response = client.post("/api/demo/reset", headers=_auth_headers("admin"))

    assert response.status_code == 200
    data = response.json()
    assert data["reset_completed"] is True
    assert "products" in data["deleted_or_disabled"]
    assert any("Unknown" in note for note in data["safety_notes"])


def test_audit_log_is_created_after_demo_seed():
    client.post("/api/demo/seed", headers=_auth_headers("admin"))
    response = client.get(
        "/api/audit-logs",
        params={"action": "demo_data_seeded", "limit": 1},
        headers=_auth_headers("admin"),
    )

    assert response.status_code == 200
    assert response.json()[0]["action"] == "demo_data_seeded"


def test_audit_log_is_created_after_full_demo_scenario():
    client.post("/api/demo/scenario/full", headers=_auth_headers("manager"))
    response = client.get(
        "/api/audit-logs",
        params={"action": "demo_full_scenario_created", "limit": 1},
        headers=_auth_headers("admin"),
    )

    assert response.status_code == 200
    assert response.json()[0]["action"] == "demo_full_scenario_created"


def test_openapi_includes_demo_paths():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/demo/status" in paths
    assert "/api/demo/seed" in paths
    assert "/api/demo/scenario/full" in paths


def test_demo_reset_does_not_disable_unknown_products():
    db = create_db_session()
    try:
        product = Product(
            name="Non Demo Product",
            sku=f"NON-DEMO-PRODUCT-{uuid4().hex[:8]}",
            category="A3 Flyer",
            active=True,
        )
        db.add(product)
        db.commit()
        product_id = product.id
    finally:
        db.close()

    response = client.post("/api/demo/reset", headers=_auth_headers("admin"))
    assert response.status_code == 200

    db = create_db_session()
    try:
        product = db.get(Product, product_id)
        assert product is not None
        assert product.active is True
    finally:
        db.close()


def create_db_session():
    from backend.db import SessionLocal

    return SessionLocal()


def _auth_headers(username: str) -> dict:
    token = _login(username, f"{username}-demo-password")
    return {"Authorization": f"Bearer {token}"}


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
