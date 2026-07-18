from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from backend.config import Settings
from backend.db import build_engine, build_session_factory
from backend.domain.roles import UserRole
from backend.main import create_app
from backend.models.user import User
from backend.services.passwords import hash_password


pytestmark = pytest.mark.postgresql


def _truncate_pricing_workflow(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE price_validation_checks, price_validation_results, price_candidate_lines, "
                "price_candidates, pricing_checks, competitor_references, competitors, cost_profiles, products, "
                "quote_revision_lines, quote_revisions, quote_lines, quotes, audit_events, customer_requests, users "
                "RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def client() -> TestClient:
    if os.getenv("QUOTEOPS_POSTGRES_INTEGRATION") != "1":
        pytest.skip("Requires an explicitly configured V2-only PostgreSQL integration database")
    settings = Settings()
    engine = build_engine(settings)
    try:
        _truncate_pricing_workflow(engine)
        session = build_session_factory(settings)()
        try:
            session.add_all(
                [
                    User(
                        username="pricing-manager",
                        display_name="Pricing Manager",
                        password_hash=hash_password("pricing-manager-pass"),
                        role=UserRole.MANAGER,
                        active=True,
                    ),
                    User(
                        username="pricing-viewer",
                        display_name="Pricing Viewer",
                        password_hash=hash_password("pricing-viewer-pass"),
                        role=UserRole.VIEWER,
                        active=True,
                    ),
                    User(
                        username="pricing-admin",
                        display_name="Pricing Admin",
                        password_hash=hash_password("pricing-admin-pass"),
                        role=UserRole.ADMIN,
                        active=True,
                    ),
                ]
            )
            session.commit()
        finally:
            session.close()
        with TestClient(create_app(settings)) as test_client:
            yield test_client
    finally:
        _truncate_pricing_workflow(engine)
        engine.dispose()


def _token(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_quote(client: TestClient, manager_headers: dict[str, str]) -> dict[str, object]:
    request = client.post(
        "/api/customer-requests",
        headers=manager_headers,
        json={
            "customer_name": "Pricing Customer",
            "contact_name": "Kim",
            "product_code": "a3_flyer",
            "quantity": 25,
        },
    )
    assert request.status_code == 201
    reviewing = client.post(
        f"/api/customer-requests/{request.json()['id']}/transitions",
        headers=manager_headers,
        json={"version": request.json()["version"], "target_status": "reviewing"},
    )
    assert reviewing.status_code == 200
    converted = client.post(
        f"/api/customer-quote-requests/{request.json()['id']}/quotes",
        headers=manager_headers,
        json={"request_version": reviewing.json()["version"], "title": "Pricing Check Quote"},
    )
    assert converted.status_code == 201
    quote = converted.json()
    lines = client.put(
        f"/api/quotes/{quote['id']}/lines",
        headers=manager_headers,
        json={
            "version": quote["version"],
            "lines": [
                {
                    "description": "A3 Flyer 25 units",
                    "product_code": "a3_flyer",
                    "quantity": 25,
                    "unit_price": "0.00",
                }
            ],
        },
    )
    assert lines.status_code == 200
    return lines.json()


def _create_source_data(
    client: TestClient,
    manager_headers: dict[str, str],
    *,
    target_margin_rate: str = "0.350000",
    reference_unit_price: str = "3000.00",
) -> dict[str, int]:
    product = client.post(
        "/api/products",
        headers={**manager_headers, "X-Request-ID": "pricing-product-001"},
        json={"code": "a3_flyer", "name": "A3 Flyer", "description": "MVP product"},
    )
    assert product.status_code == 201
    cost_profile = client.post(
        "/api/cost-profiles",
        headers=manager_headers,
        json={
            "product_id": product.json()["id"],
            "material_cost": "1000.00",
            "labor_cost": "500.00",
            "overhead_cost": "500.00",
            "target_margin_rate": target_margin_rate,
        },
    )
    assert cost_profile.status_code == 201
    competitor = client.post(
        "/api/competitors",
        headers=manager_headers,
        json={"name": "Local Reference", "competitor_type": "local_shop"},
    )
    assert competitor.status_code == 201
    reference = client.post(
        "/api/competitor-references",
        headers=manager_headers,
        json={
            "competitor_id": competitor.json()["id"],
            "product_id": product.json()["id"],
            "quantity": 25,
            "price_basis": "unit_price",
            "reference_price": reference_unit_price,
            "observed_at": "2026-07-17T10:00:00Z",
        },
    )
    assert reference.status_code == 201
    return {"product_id": product.json()["id"], "cost_profile_id": cost_profile.json()["id"]}


def _create_pricing_check(
    client: TestClient,
    manager_headers: dict[str, str],
    quote: dict[str, object],
    *,
    selected_strategy: str = "target_margin",
    include_competitor_context: bool = True,
) -> dict[str, object]:
    response = client.post(
        f"/api/quotes/{quote['id']}/pricing-checks",
        headers={**manager_headers, "X-Request-ID": "pricing-check-001"},
        json={
            "quote_version": quote["version"],
            "quote_revision_id": quote["current_revision"]["id"],
            "selected_strategy": selected_strategy,
            "include_competitor_context": include_competitor_context,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_pricing_check_persists_exact_candidates_role_safe_detail_and_audit(client: TestClient) -> None:
    manager_headers = _token(client, "pricing-manager", "pricing-manager-pass")
    viewer_headers = _token(client, "pricing-viewer", "pricing-viewer-pass")
    assert client.post("/api/products", json={"code": "a3_flyer", "name": "No auth"}).status_code == 401
    source = _create_source_data(client, manager_headers)
    quote = _create_quote(client, manager_headers)
    check = _create_pricing_check(client, manager_headers, quote)

    assert check["status"] == "ready"
    assert check["candidate_count"] == 3
    assert check["selected_strategy"] == "target_margin"
    assert check["selected_total_price"] == "76923.08"
    assert check["selected_gross_profit"] == "26923.08"
    assert check["selected_margin_rate"] == "0.350000"
    assert check["competitor_context"] == {
        "included": True,
        "reference_count": 1,
        "average_unit_price": "3000.00",
        "source_version": "competitor-reference-v1",
        "earliest_observed_at": "2026-07-17T10:00:00Z",
        "latest_observed_at": "2026-07-17T10:00:00Z",
    }
    candidates = {candidate["strategy"]: candidate for candidate in check["candidates"]}
    assert candidates["low_margin"]["validation"]["status"] == "failed"
    assert candidates["low_margin"]["validation"]["risk_level"] == "high"
    assert candidates["target_margin"]["validation"]["status"] == "passed"
    assert candidates["target_margin"]["lines"] == [
        {
            "id": candidates["target_margin"]["lines"][0]["id"],
            "position": 1,
            "product_code": "a3_flyer",
            "quantity": 25,
            "unit_price": "3076.92",
            "total_price": "76923.08",
        }
    ]
    assert "material_cost" not in str(check).lower()
    assert "labor_cost" not in str(check).lower()
    assert "overhead_cost" not in str(check).lower()
    assert "cost_profile_id" not in str(check).lower()

    viewer_detail = client.get(f"/api/pricing-checks/{check['id']}", headers=viewer_headers)
    assert viewer_detail.status_code == 200
    assert viewer_detail.json()["id"] == check["id"]
    assert "material_cost" not in str(viewer_detail.json()).lower()
    assert client.get("/api/cost-profiles", headers=viewer_headers).status_code == 403
    assert client.get("/api/competitor-references", headers=viewer_headers).status_code == 403

    listing = client.get(f"/api/quotes/{quote['id']}/pricing-checks", headers=viewer_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == check["id"]

    settings = Settings()
    engine = build_engine(settings)
    try:
        with engine.connect() as connection:
            actions = connection.execute(
                text("SELECT action FROM audit_events ORDER BY id")
            ).scalars().all()
            metadata = connection.execute(
                text("SELECT CAST(metadata_json AS TEXT) FROM audit_events WHERE action = 'pricing_check.created'")
            ).scalar_one().lower()
        assert "pricing_check.created" in actions
        assert "material_cost" not in metadata
        assert "reference_price" not in metadata
        with engine.connect() as connection:
            with connection.begin():
                with pytest.raises(DBAPIError, match="pricing evidence is immutable"):
                    with connection.begin_nested():
                        connection.execute(
                            text("UPDATE pricing_checks SET selected_strategy = 'low_margin' WHERE id = :id"),
                            {"id": check["id"]},
                        )
    finally:
        engine.dispose()

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert {
        "/api/products",
        "/api/cost-profiles",
        "/api/competitors",
        "/api/competitor-references",
        "/api/quotes/{quote_id}/pricing-checks",
        "/api/pricing-checks/{pricing_check_id}",
    }.issubset(set(openapi.json()["paths"]))


def test_pricing_check_warning_blocked_and_missing_source_contracts(client: TestClient) -> None:
    manager_headers = _token(client, "pricing-manager", "pricing-manager-pass")
    viewer_headers = _token(client, "pricing-viewer", "pricing-viewer-pass")
    quote_without_source = _create_quote(client, manager_headers)
    missing_source = client.post(
        f"/api/quotes/{quote_without_source['id']}/pricing-checks",
        headers=manager_headers,
        json={
            "quote_version": quote_without_source["version"],
            "quote_revision_id": quote_without_source["current_revision"]["id"],
        },
    )
    assert missing_source.status_code == 409
    assert missing_source.json()["code"] == "active_product_not_found"

    source = _create_source_data(client, manager_headers, target_margin_rate="0.250000", reference_unit_price="10000.00")
    warning = _create_pricing_check(client, manager_headers, quote_without_source)
    assert warning["status"] == "needs_review"
    assert warning["validation_status"] == "warning"
    assert warning["risk_level"] == "medium"
    assert next(item for item in warning["candidates"] if item["is_selected"])["validation"]["checks"][2]["code"] == "market_floor"

    replacement_profile = client.post(
        "/api/cost-profiles",
        headers=manager_headers,
        json={
            "product_id": source["product_id"],
            "material_cost": "1000.00",
            "labor_cost": "500.00",
            "overhead_cost": "500.00",
            "target_margin_rate": "0.500000",
        },
    )
    assert replacement_profile.status_code == 201
    blocked = _create_pricing_check(
        client,
        manager_headers,
        quote_without_source,
        selected_strategy="premium_margin",
        include_competitor_context=False,
    )
    assert blocked["status"] == "blocked"
    assert blocked["validation_status"] == "failed"
    assert blocked["risk_level"] == "high"
    assert client.post(
        f"/api/quotes/{quote_without_source['id']}/pricing-checks",
        headers=viewer_headers,
        json={
            "quote_version": quote_without_source["version"],
            "quote_revision_id": quote_without_source["current_revision"]["id"],
        },
    ).status_code == 403

    stale = client.post(
        f"/api/quotes/{quote_without_source['id']}/pricing-checks",
        headers=manager_headers,
        json={
            "quote_version": quote_without_source["version"] - 1,
            "quote_revision_id": quote_without_source["current_revision"]["id"],
        },
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "stale_quote"
