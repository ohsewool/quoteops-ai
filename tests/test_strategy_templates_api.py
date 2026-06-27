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


def test_create_strategy_template_successfully():
    response = _create_template()

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Strategy"
    assert data["strategy_code"].startswith("test_strategy_")
    assert data["margin_rates"] == [0.22, 0.33, 0.44]
    assert data["default_quantities"] == [5, 25, 100]
    assert data["risk_preference"] == "balanced"
    assert data["active"] is True


def test_list_strategy_templates():
    created = _create_template().json()
    response = client.get("/api/strategy-templates", headers=_auth_headers("viewer"))

    assert response.status_code == 200
    assert any(template["id"] == created["id"] for template in response.json())
    assert any(template["strategy_code"] == "standard_margin" for template in response.json())


def test_get_strategy_template_by_id():
    created = _create_template().json()
    response = client.get(
        f"/api/strategy-templates/{created['id']}",
        headers=_auth_headers("viewer"),
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_update_strategy_template():
    created = _create_template().json()
    response = client.put(
        f"/api/strategy-templates/{created['id']}",
        headers=_auth_headers("manager"),
        json={
            "name": "Updated Strategy",
            "margin_rates": [0.3, 0.4],
            "default_quantities": [10, 50],
            "risk_preference": "aggressive",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Strategy"
    assert data["margin_rates"] == [0.3, 0.4]
    assert data["default_quantities"] == [10, 50]
    assert data["risk_preference"] == "aggressive"


def test_disable_strategy_template():
    created = _create_template().json()
    response = client.delete(
        f"/api/strategy-templates/{created['id']}",
        headers=_auth_headers("manager"),
    )

    assert response.status_code == 200
    assert response.json()["active"] is False


def test_duplicate_strategy_code_returns_error():
    created = _create_template().json()
    response = _create_template(strategy_code=created["strategy_code"])

    assert response.status_code == 400


def test_invalid_margin_rate_returns_error():
    response = _create_template(margin_rates=[0.25, 1])

    assert response.status_code == 422


def test_apply_template_to_candidate_prices_successfully():
    created = _create_template(include_competitor_context_default=True).json()
    response = client.post(
        f"/api/strategy-templates/{created['id']}/candidate-prices",
        headers=_auth_headers("viewer"),
        json={"product_id": 1, "quantity": 10},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["product_id"] == 1
    assert data["quantity"] == 10
    assert [candidate["margin_rate"] for candidate in data["candidates"]] == [0.22, 0.33, 0.44]
    assert data["competitor_context"]["reference_price_count"] == 2


def test_apply_template_to_pricing_simulation_successfully():
    created = _create_template().json()
    response = client.post(
        f"/api/strategy-templates/{created['id']}/pricing-simulation",
        headers=_auth_headers("viewer"),
        json={"name": "Simulation from strategy", "product_id": 1},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Simulation from strategy"
    assert data["scenario_count"] == 9
    assert {scenario["quantity"] for scenario in data["scenarios"]} == {5, 25, 100}
    assert {scenario["margin_rate"] for scenario in data["scenarios"]} == {0.22, 0.33, 0.44}


def test_inactive_template_cannot_be_applied():
    created = _create_template(active=False).json()
    response = client.post(
        f"/api/strategy-templates/{created['id']}/candidate-prices",
        headers=_auth_headers("viewer"),
        json={"product_id": 1, "quantity": 10},
    )

    assert response.status_code == 400


def test_missing_template_returns_404():
    response = client.get("/api/strategy-templates/999999", headers=_auth_headers("viewer"))

    assert response.status_code == 404


def test_audit_log_is_created_after_template_creation():
    created = _create_template().json()
    response = client.get(
        "/api/audit-logs",
        params={"action": "strategy_template_created", "limit": 1},
        headers=_auth_headers("admin"),
    )

    assert response.status_code == 200
    log = response.json()[0]
    assert log["entity_id"] == str(created["id"])
    assert '"strategy_code"' in log["metadata_json"]


def test_audit_log_is_created_after_template_application():
    created = _create_template().json()
    response = client.post(
        f"/api/strategy-templates/{created['id']}/candidate-prices",
        headers=_auth_headers("viewer"),
        json={"product_id": 1, "quantity": 10},
    )
    assert response.status_code == 200

    logs = client.get(
        "/api/audit-logs",
        params={"action": "strategy_template_candidate_prices_generated", "limit": 1},
        headers=_auth_headers("admin"),
    )

    assert logs.status_code == 200
    assert logs.json()[0]["entity_id"] == str(created["id"])


def test_openapi_includes_strategy_templates_paths():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/strategy-templates" in paths
    assert "/api/strategy-templates/{template_id}" in paths
    assert "/api/strategy-templates/{template_id}/candidate-prices" in paths
    assert "/api/strategy-templates/{template_id}/pricing-simulation" in paths


def _create_template(
    *,
    strategy_code: str | None = None,
    margin_rates: list[float] | None = None,
    include_competitor_context_default: bool = False,
    active: bool = True,
):
    resolved_code = strategy_code or f"test_strategy_{uuid4().hex[:10]}"
    return client.post(
        "/api/strategy-templates",
        headers=_auth_headers("manager"),
        json={
            "name": "Test Strategy",
            "strategy_code": resolved_code,
            "description": "Test deterministic strategy template.",
            "margin_rates": margin_rates or [0.22, 0.33, 0.44],
            "default_quantities": [5, 25, 100],
            "include_competitor_context_default": include_competitor_context_default,
            "risk_preference": "balanced",
            "active": active,
            "notes": "Test template.",
        },
    )


def _auth_headers(username: str) -> dict:
    token = _login(username, f"{username}-demo-password")
    return {"Authorization": f"Bearer {token}"}


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
