from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, text

from backend.config import Settings
from backend.db import build_engine, build_session_factory
from backend.domain.roles import UserRole
from backend.main import create_app
from backend.models.user import User
from backend.services.passwords import hash_password

pytestmark = pytest.mark.postgresql


@pytest.fixture
def client() -> TestClient:
    if os.getenv("QUOTEOPS_POSTGRES_INTEGRATION") != "1":
        pytest.skip("Requires an explicitly configured V2-only PostgreSQL integration database")
    settings = Settings()
    engine = build_engine(settings)
    try:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE audit_events, customer_requests, users RESTART IDENTITY CASCADE"))
        session = build_session_factory(settings)()
        try:
            session.add_all(
                [
                    User(username="manager", display_name="Manager", password_hash=hash_password("manager-test-pass"), role=UserRole.MANAGER, active=True),
                    User(username="viewer", display_name="Viewer", password_hash=hash_password("viewer-test-pass"), role=UserRole.VIEWER, active=True),
                    User(username="admin", display_name="Admin", password_hash=hash_password("admin-test-pass"), role=UserRole.ADMIN, active=True),
                ]
            )
            session.commit()
        finally:
            session.close()
        app = create_app(settings)
        with TestClient(app) as test_client:
            yield test_client
    finally:
        with engine.begin() as connection:
            connection.execute(text("TRUNCATE TABLE audit_events, customer_requests, users RESTART IDENTITY CASCADE"))
        engine.dispose()


def token(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_request(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    response = client.post(
        "/api/customer-requests",
        headers={**headers, "X-Request-ID": "request-create-001"},
        json={
            "customer_name": "Acme Print",
            "contact_name": "Kim",
            "product_code": "a3_flyer",
            "quantity": 100,
            "notes": "Need a safe quote workflow.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_customer_request_role_matrix_state_conflict_and_audit(client: TestClient) -> None:
    manager_headers = token(client, "manager", "manager-test-pass")
    viewer_headers = token(client, "viewer", "viewer-test-pass")
    anonymous_list = client.get("/api/customer-requests")
    assert anonymous_list.status_code == 401
    anonymous_create = client.post(
        "/api/customer-requests",
        json={"customer_name": "Public write", "product_code": "a3_flyer", "quantity": 1},
    )
    assert anonymous_create.status_code == 401
    created = create_request(client, manager_headers)
    assert created["status"] == "new"
    assert created["version"] == 1
    assert created["ready_for_quote_conversion"] is False

    viewer_write = client.post(
        "/api/customer-requests",
        headers=viewer_headers,
        json={"customer_name": "No write", "product_code": "brand_sticker", "quantity": 10},
    )
    assert viewer_write.status_code == 403
    assert viewer_write.json()["code"] == "permission_denied"

    reviewed = client.post(
        f"/api/customer-requests/{created['id']}/transitions",
        headers=manager_headers,
        json={"version": 1, "target_status": "reviewing"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "reviewing"
    assert reviewed.json()["ready_for_quote_conversion"] is True
    assert reviewed.json()["allowed_transitions"] == ["cancelled"]

    stale_update = client.patch(
        f"/api/customer-requests/{created['id']}",
        headers=manager_headers,
        json={"version": 1, "quantity": 125},
    )
    assert stale_update.status_code == 409
    assert stale_update.json()["code"] == "stale_customer_request"

    premature_quote = client.post(
        f"/api/customer-requests/{created['id']}/transitions",
        headers=manager_headers,
        json={"version": 2, "target_status": "quoted"},
    )
    assert premature_quote.status_code == 409
    assert premature_quote.json()["code"] == "quote_conversion_required"

    audit = client.get(f"/api/customer-requests/{created['id']}/audit-events", headers=viewer_headers)
    assert audit.status_code == 200
    assert [item["action"] for item in audit.json()["items"]] == [
        "customer_request.created",
        "customer_request.transitioned",
    ]
    assert all(item["actor_username"] == "manager" for item in audit.json()["items"])


def test_customer_request_listing_validation_and_not_found(client: TestClient) -> None:
    manager_headers = token(client, "manager", "manager-test-pass")
    viewer_headers = token(client, "viewer", "viewer-test-pass")
    created = create_request(client, manager_headers)

    listing = client.get("/api/customer-requests", headers=viewer_headers, params={"status": "new", "search": "Acme"})
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == created["id"]

    invalid_quantity = client.post(
        "/api/customer-requests",
        headers=manager_headers,
        json={"customer_name": "Invalid", "product_code": "brand_sticker", "quantity": 0},
    )
    assert invalid_quantity.status_code == 422
    assert invalid_quantity.json()["code"] == "validation_error"

    missing = client.get("/api/customer-requests/999999", headers=viewer_headers)
    assert missing.status_code == 404
    assert missing.json()["code"] == "customer_request_not_found"


def test_customer_request_postgresql_schema_contract() -> None:
    if os.getenv("QUOTEOPS_POSTGRES_INTEGRATION") != "1":
        pytest.skip("Requires an explicitly configured V2-only PostgreSQL integration database")
    engine = build_engine(Settings())
    try:
        inspector = inspect(engine)
        assert "customer_requests" in inspector.get_table_names()
        constraints = {item["name"] for item in inspector.get_check_constraints("customer_requests")}
        assert {
            "ck_customer_requests_positive_quantity",
            "ck_customer_requests_positive_version",
        }.issubset(constraints)
        foreign_keys = inspector.get_foreign_keys("customer_requests")
        assert {item["referred_table"] for item in foreign_keys} == {"users"}
        indexes = {item["name"] for item in inspector.get_indexes("customer_requests")}
        assert {
            "ix_customer_requests_assignee_user_id",
            "ix_customer_requests_created_at",
            "ix_customer_requests_due_date",
            "ix_customer_requests_product_code",
            "ix_customer_requests_status",
        }.issubset(indexes)
        with engine.connect() as connection:
            status_values = connection.execute(
                text(
                    "SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_type.oid = pg_enum.enumtypid "
                    "WHERE pg_type.typname = 'customer_request_status' ORDER BY enumsortorder"
                )
            ).scalars().all()
            product_values = connection.execute(
                text(
                    "SELECT enumlabel FROM pg_enum JOIN pg_type ON pg_type.oid = pg_enum.enumtypid "
                    "WHERE pg_type.typname = 'product_code' ORDER BY enumsortorder"
                )
            ).scalars().all()
        assert status_values == ["new", "reviewing", "quoted", "closed", "cancelled"]
        assert product_values == ["a3_flyer", "brand_sticker"]
    finally:
        engine.dispose()


def test_customer_request_openapi_contract(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert {
        "/api/customer-requests",
        "/api/customer-requests/{customer_request_id}",
        "/api/customer-requests/{customer_request_id}/transitions",
        "/api/customer-requests/{customer_request_id}/audit-events",
    }.issubset(set(response.json()["paths"]))
