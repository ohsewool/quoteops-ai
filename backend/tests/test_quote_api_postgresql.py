from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.config import Settings
from backend.db import build_engine, build_session_factory
from backend.domain.roles import UserRole
from backend.main import create_app
from backend.models.user import User
from backend.services.passwords import hash_password


pytestmark = pytest.mark.postgresql


def _truncate_quote_workflow(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE quote_revision_lines, quote_revisions, quote_lines, quotes, "
                "audit_events, customer_requests, users RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def client() -> TestClient:
    if os.getenv("QUOTEOPS_POSTGRES_INTEGRATION") != "1":
        pytest.skip("Requires an explicitly configured V2-only PostgreSQL integration database")
    settings = Settings()
    engine = build_engine(settings)
    try:
        _truncate_quote_workflow(engine)
        session = build_session_factory(settings)()
        try:
            session.add_all(
                [
                    User(username="quote-manager", display_name="Quote Manager", password_hash=hash_password("quote-manager-pass"), role=UserRole.MANAGER, active=True),
                    User(username="quote-viewer", display_name="Quote Viewer", password_hash=hash_password("quote-viewer-pass"), role=UserRole.VIEWER, active=True),
                    User(username="quote-admin", display_name="Quote Admin", password_hash=hash_password("quote-admin-pass"), role=UserRole.ADMIN, active=True),
                ]
            )
            session.commit()
        finally:
            session.close()
        app = create_app(settings)
        with TestClient(app) as test_client:
            yield test_client
    finally:
        _truncate_quote_workflow(engine)
        engine.dispose()


def token(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_reviewing_request(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    created = client.post(
        "/api/customer-requests",
        headers=headers,
        json={
            "customer_name": "Quote Customer",
            "contact_name": "Kim",
            "product_code": "a3_flyer",
            "quantity": 25,
            "notes": "Quote lineage test request.",
        },
    )
    assert created.status_code == 201
    reviewed = client.post(
        f"/api/customer-requests/{created.json()['id']}/transitions",
        headers=headers,
        json={"version": 1, "target_status": "reviewing"},
    )
    assert reviewed.status_code == 200
    return reviewed.json()


def convert_request(client: TestClient, headers: dict[str, str]) -> tuple[dict[str, object], dict[str, object]]:
    customer_request = create_reviewing_request(client, headers)
    converted = client.post(
        f"/api/customer-quote-requests/{customer_request['id']}/quotes",
        headers={**headers, "X-Request-ID": "quote-convert-001"},
        json={"request_version": customer_request["version"], "title": "Initial Customer Quote"},
    )
    assert converted.status_code == 201
    return customer_request, converted.json()


def test_quote_conversion_has_request_lineage_revisions_and_role_enforcement(client: TestClient) -> None:
    manager_headers = token(client, "quote-manager", "quote-manager-pass")
    viewer_headers = token(client, "quote-viewer", "quote-viewer-pass")
    assert client.post("/api/customer-quote-requests/1/quotes", json={"request_version": 1}).status_code == 401
    assert client.post(
        "/api/customer-quote-requests/1/quotes",
        headers=viewer_headers,
        json={"request_version": 1},
    ).status_code == 403

    customer_request, quote = convert_request(client, manager_headers)
    assert quote["status"] == "draft"
    assert quote["currency"] == "KRW"
    assert quote["total_amount"] == "0.00"
    assert quote["version"] == 1
    assert quote["current_revision_number"] == 1
    assert quote["lines"] == []
    assert quote["current_revision"]["revision_number"] == 1
    assert quote["current_revision"]["line_count"] == 0
    assert quote["customer_request_id"] == customer_request["id"]

    quoted_request = client.get(f"/api/customer-requests/{customer_request['id']}", headers=viewer_headers)
    assert quoted_request.status_code == 200
    assert quoted_request.json()["status"] == "quoted"
    assert quoted_request.json()["version"] == 3

    revisions = client.get(f"/api/quotes/{quote['id']}/revisions", headers=viewer_headers)
    assert revisions.status_code == 200
    assert revisions.json()["total"] == 1
    revision_id = revisions.json()["items"][0]["id"]
    revision = client.get(f"/api/quote-revisions/{revision_id}", headers=viewer_headers)
    assert revision.status_code == 200
    assert revision.json()["quote_id"] == quote["id"]
    assert revision.json()["lines"] == []

    duplicate = client.post(
        f"/api/customer-quote-requests/{customer_request['id']}/quotes",
        headers=manager_headers,
        json={"request_version": 3},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "request_not_convertible"


def test_quote_draft_lines_revisions_and_conflicts_are_deterministic(client: TestClient) -> None:
    manager_headers = token(client, "quote-manager", "quote-manager-pass")
    viewer_headers = token(client, "quote-viewer", "quote-viewer-pass")
    _, quote = convert_request(client, manager_headers)

    viewer_write = client.put(
        f"/api/quotes/{quote['id']}/lines",
        headers=viewer_headers,
        json={"version": 1, "lines": []},
    )
    assert viewer_write.status_code == 403

    lines = client.put(
        f"/api/quotes/{quote['id']}/lines",
        headers={**manager_headers, "X-Request-ID": "quote-lines-001"},
        json={
            "version": 1,
            "lines": [
                {
                    "description": "A3 Flyer printing",
                    "product_code": "a3_flyer",
                    "quantity": 25,
                    "unit_price": "1000.005",
                    "options": {"paper": "matte"},
                },
                {
                    "description": "A3 Flyer setup",
                    "product_code": "a3_flyer",
                    "quantity": 1,
                    "unit_price": "100.50",
                    "options": {},
                },
            ],
        },
    )
    assert lines.status_code == 200
    lines_payload = lines.json()
    assert lines_payload["version"] == 2
    assert lines_payload["current_revision_number"] == 2
    assert lines_payload["lines"][0]["unit_price"] == "1000.01"
    assert lines_payload["lines"][0]["line_total"] == "25000.25"
    assert lines_payload["total_amount"] == "25100.75"
    assert lines_payload["current_revision"]["line_count"] == 2

    stale = client.put(
        f"/api/quotes/{quote['id']}/lines",
        headers=manager_headers,
        json={"version": 1, "lines": []},
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "stale_quote"

    float_price = client.put(
        f"/api/quotes/{quote['id']}/lines",
        headers=manager_headers,
        json={
            "version": 2,
            "lines": [{"description": "Float is unsafe", "product_code": "a3_flyer", "quantity": 1, "unit_price": 10.5}],
        },
    )
    assert float_price.status_code == 422
    assert float_price.json()["code"] == "validation_error"

    metadata = client.patch(
        f"/api/quotes/{quote['id']}",
        headers=manager_headers,
        json={"version": 2, "title": "Updated Customer Quote", "notes": "Manager-reviewed metadata."},
    )
    assert metadata.status_code == 200
    assert metadata.json()["version"] == 3
    assert metadata.json()["current_revision_number"] == 3
    assert metadata.json()["title"] == "Updated Customer Quote"
    assert metadata.json()["total_amount"] == "25100.75"

    null_title = client.patch(
        f"/api/quotes/{quote['id']}",
        headers=manager_headers,
        json={"version": 3, "title": None},
    )
    assert null_title.status_code == 422
    assert null_title.json()["code"] == "invalid_quote_title"

    revision_page = client.get(f"/api/quotes/{quote['id']}/revisions", headers=viewer_headers)
    assert revision_page.status_code == 200
    assert [item["revision_number"] for item in revision_page.json()["items"]] == [3, 2, 1]
    second_revision_id = next(item["id"] for item in revision_page.json()["items"] if item["revision_number"] == 2)
    second_revision = client.get(f"/api/quote-revisions/{second_revision_id}", headers=viewer_headers)
    assert second_revision.status_code == 200
    assert second_revision.json()["title"] == "Initial Customer Quote"
    assert second_revision.json()["total_amount"] == "25100.75"
    assert len(second_revision.json()["lines"]) == 2


def test_quote_list_errors_audit_and_openapi_contract(client: TestClient) -> None:
    manager_headers = token(client, "quote-manager", "quote-manager-pass")
    viewer_headers = token(client, "quote-viewer", "quote-viewer-pass")
    _, quote = convert_request(client, manager_headers)
    client.put(
        f"/api/quotes/{quote['id']}/lines",
        headers=manager_headers,
        json={"version": 1, "lines": []},
    )

    assert client.get("/api/quotes").status_code == 401
    listing = client.get("/api/quotes", headers=viewer_headers, params={"status": "draft", "customer": "Quote"})
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == quote["id"]
    assert client.get("/api/quotes", headers=viewer_headers, params={"page": 0}).status_code == 422
    missing = client.get("/api/quotes/999999", headers=viewer_headers)
    assert missing.status_code == 404
    assert missing.json()["code"] == "quote_not_found"

    settings = Settings()
    engine = build_engine(settings)
    try:
        with engine.connect() as connection:
            actions = connection.execute(
                text("SELECT action FROM audit_events WHERE entity_type = 'quote' ORDER BY id")
            ).scalars().all()
            metadata_text = connection.execute(
                text("SELECT CAST(metadata_json AS TEXT) FROM audit_events WHERE entity_type = 'quote' ORDER BY id LIMIT 1")
            ).scalar_one().lower()
        assert actions == ["quote.created", "quote.lines_replaced"]
        assert "quote customer" not in metadata_text
        assert "token" not in metadata_text
    finally:
        engine.dispose()

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert {
        "/api/customer-quote-requests/{customer_request_id}/quotes",
        "/api/quotes",
        "/api/quotes/{quote_id}",
        "/api/quotes/{quote_id}/lines",
        "/api/quotes/{quote_id}/revisions",
        "/api/quote-revisions/{revision_id}",
    }.issubset(set(openapi.json()["paths"]))
