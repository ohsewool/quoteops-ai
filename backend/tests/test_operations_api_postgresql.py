from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text

from backend.config import Settings
from backend.db import build_engine, build_session_factory
from backend.domain.roles import UserRole
from backend.main import create_app
from backend.models.audit_event import AuditEvent
from backend.models.customer_request import CustomerRequest
from backend.models.user import User
from backend.services.audit import append_audit_event
from backend.services.passwords import hash_password


pytestmark = pytest.mark.postgresql


def _truncate_operations_workflow(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE demo_runs, copilot_outputs, html_reports, approval_decisions, approval_requests, "
                "price_validation_checks, price_validation_results, price_candidate_lines, price_candidates, "
                "pricing_checks, competitor_references, competitors, cost_profiles, products, "
                "quote_revision_lines, quote_revisions, quote_lines, quotes, audit_events, "
                "customer_requests, users RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture
def client() -> TestClient:
    if os.getenv("QUOTEOPS_POSTGRES_INTEGRATION") != "1":
        pytest.skip("Requires an explicitly configured V2-only PostgreSQL integration database")
    settings = Settings(demo_enabled=True)
    engine = build_engine(settings)
    try:
        _truncate_operations_workflow(engine)
        session = build_session_factory(settings)()
        try:
            session.add_all(
                [
                    User(username="operations-admin", display_name="Operations Admin", password_hash=hash_password("operations-admin-pass"), role=UserRole.ADMIN, active=True),
                    User(username="operations-manager", display_name="Operations Manager", password_hash=hash_password("operations-manager-pass"), role=UserRole.MANAGER, active=True),
                    User(username="operations-viewer", display_name="Operations Viewer", password_hash=hash_password("operations-viewer-pass"), role=UserRole.VIEWER, active=True),
                ]
            )
            session.commit()
        finally:
            session.close()
        with TestClient(create_app(settings)) as test_client:
            yield test_client
    finally:
        _truncate_operations_workflow(engine)
        engine.dispose()


def _token(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _source_records(client: TestClient, headers: dict[str, str]) -> tuple[int, int]:
    product = client.post(
        "/api/products",
        headers=headers,
        json={"code": "a3_flyer", "name": "A3 Flyer", "description": "CSV source product"},
    )
    assert product.status_code == 201, product.text
    competitor = client.post(
        "/api/competitors",
        headers=headers,
        json={"name": "CSV Reference", "competitor_type": "local_shop"},
    )
    assert competitor.status_code == 201, competitor.text
    return product.json()["id"], competitor.json()["id"]


def test_competitor_reference_csv_adapter_is_atomic_and_role_safe(client: TestClient) -> None:
    manager_headers = _token(client, "operations-manager", "operations-manager-pass")
    viewer_headers = _token(client, "operations-viewer", "operations-viewer-pass")
    product_id, competitor_id = _source_records(client, manager_headers)
    valid_csv = (
        "product_id,competitor_id,quantity,price_basis,reference_price,observed_at,source_note\n"
        f"{product_id},{competitor_id},25,unit_price,3000.00,2026-07-18T10:00:00+00:00,public competitor listing\n"
    )

    denied = client.post(
        "/api/operations/competitor-references/import",
        headers=viewer_headers,
        json={"schema_version": "competitor-reference-csv-v1", "csv_text": valid_csv},
    )
    assert denied.status_code == 403
    assert client.get("/api/operations/competitor-references/export", headers=viewer_headers).status_code == 403

    malformed_csv = valid_csv.replace("3000.00", "3000.123")
    rejected = client.post(
        "/api/operations/competitor-references/import",
        headers=manager_headers,
        json={"schema_version": "competitor-reference-csv-v1", "csv_text": malformed_csv},
    )
    assert rejected.status_code == 422
    assert rejected.json()["code"] == "csv_import_invalid"

    imported = client.post(
        "/api/operations/competitor-references/import",
        headers=manager_headers,
        json={"schema_version": "competitor-reference-csv-v1", "csv_text": valid_csv},
    )
    assert imported.status_code == 200, imported.text
    assert imported.json() == {
        "schema_version": "competitor-reference-csv-v1",
        "imported_count": 1,
        "product_ids": [product_id],
        "competitor_ids": [competitor_id],
    }

    exported = client.get("/api/operations/competitor-references/export", headers=manager_headers)
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert "product_id,competitor_id,quantity,price_basis,reference_price,observed_at,source_note" in exported.text
    assert "3000.00" in exported.text
    assert "material_cost" not in exported.text.lower()

    settings = Settings()
    engine = build_engine(settings)
    try:
        with engine.connect() as connection:
            reference_count = connection.scalar(text("SELECT count(*) FROM competitor_references"))
            actions = connection.execute(
                text("SELECT action FROM audit_events WHERE action LIKE 'operations.competitor_reference_csv_%' ORDER BY id")
            ).scalars().all()
        assert reference_count == 1
        assert actions == [
            "operations.competitor_reference_csv_imported",
            "operations.competitor_reference_csv_exported",
        ]
    finally:
        engine.dispose()


def test_operations_diagnostics_and_audit_search_are_admin_safe(client: TestClient) -> None:
    admin_headers = _token(client, "operations-admin", "operations-admin-pass")
    viewer_headers = _token(client, "operations-viewer", "operations-viewer-pass")
    settings = Settings()
    session = build_session_factory(settings)()
    try:
        admin = session.scalar(select(User).where(User.username == "operations-admin"))
        assert admin is not None
        append_audit_event(
            session,
            actor_user_id=admin.id,
            action="operations.sensitive_fixture",
            entity_type="fixture",
            entity_id="safe",
            request_id="operations-test",
            metadata={"database_url": "private-value", "nested": {"password": "private-value"}, "safe": "visible"},
        )
        session.commit()
    finally:
        session.close()

    assert client.get("/api/operations/diagnostics", headers=viewer_headers).status_code == 403
    assert client.get("/api/operations/audit-events", headers=viewer_headers).status_code == 403
    diagnostics = client.get("/api/operations/diagnostics", headers=admin_headers)
    assert diagnostics.status_code == 200
    assert diagnostics.json()["database_ready"] is True
    assert "postgresql" not in diagnostics.text.lower()
    assert "password" not in diagnostics.text.lower()
    assert "secret" not in diagnostics.text.lower()

    audit = client.get(
        "/api/operations/audit-events?action=operations.sensitive_fixture",
        headers=admin_headers,
    )
    assert audit.status_code == 200
    assert audit.json()["total"] == 1
    assert audit.json()["items"][0]["metadata"] == {
        "database_url": "[REDACTED]",
        "nested": {"password": "[REDACTED]"},
        "safe": "visible",
    }
    assert "private-value" not in audit.text

    client.get(
        "/api/operations/audit-events?action=raw-filter-value-that-must-not-be-logged",
        headers=admin_headers,
    )
    session = build_session_factory(settings)()
    try:
        search_metadata = session.scalar(
            select(AuditEvent.metadata_json)
            .where(AuditEvent.action == "operations.audit_search_viewed")
            .order_by(AuditEvent.id.desc())
        )
        assert search_metadata == {
            "has_action_filter": True,
            "has_entity_type_filter": False,
            "has_actor_user_id_filter": False,
        }
        assert "raw-filter-value-that-must-not-be-logged" not in str(search_metadata)
    finally:
        session.close()

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert {
        "/api/operations/diagnostics",
        "/api/operations/audit-events",
        "/api/operations/competitor-references/import",
        "/api/operations/competitor-references/export",
    }.issubset(set(openapi.json()["paths"]))


def test_guided_demo_is_explicit_admin_only_and_reset_preserves_workflow_records(client: TestClient) -> None:
    admin_headers = _token(client, "operations-admin", "operations-admin-pass")
    manager_headers = _token(client, "operations-manager", "operations-manager-pass")
    viewer_headers = _token(client, "operations-viewer", "operations-viewer-pass")
    assert client.post("/api/demo/runs", headers=manager_headers, json={}).status_code == 403
    assert client.post("/api/demo/runs", headers=viewer_headers, json={}).status_code == 403

    settings = Settings()
    engine = build_engine(settings)
    try:
        with engine.connect() as connection:
            user_count_before = connection.scalar(text("SELECT count(*) FROM users"))
    finally:
        engine.dispose()
    started = client.post("/api/demo/runs", headers=admin_headers, json={})
    assert started.status_code == 201, started.text
    run = started.json()
    assert run["status"] == "ready"
    assert run["guide"]["total_steps"] == 6
    assert run["product_codes"] == ["a3_flyer", "brand_sticker"]
    assert len(run["artifacts"]["customer_request_ids"]) == 2

    engine = build_engine(settings)
    try:
        with engine.connect() as connection:
            user_count_after = connection.scalar(text("SELECT count(*) FROM users"))
            product_codes = connection.execute(text("SELECT code::text FROM products ORDER BY code")).scalars().all()
        assert user_count_after == user_count_before
        assert product_codes == ["a3_flyer", "brand_sticker"]
    finally:
        engine.dispose()

    unrelated = client.post(
        "/api/customer-requests",
        headers=manager_headers,
        json={"customer_name": "Non-demo record", "product_code": "a3_flyer", "quantity": 10},
    )
    assert unrelated.status_code == 201
    for _ in range(2):
        advanced = client.post(
            f"/api/demo/runs/{run['id']}/advance",
            headers=admin_headers,
            json={"version": run["version"]},
        )
        assert advanced.status_code == 200
        run = advanced.json()

    engine = build_engine(settings)
    try:
        with engine.connect() as connection:
            customer_request_count_before_reset = connection.scalar(text("SELECT count(*) FROM customer_requests"))
    finally:
        engine.dispose()
    reset = client.post(
        f"/api/demo/runs/{run['id']}/reset",
        headers=admin_headers,
        json={"version": run["version"]},
    )
    assert reset.status_code == 200
    assert reset.json()["status"] == "ready"
    assert reset.json()["current_step"] == 0

    engine = build_engine(settings)
    try:
        with engine.connect() as connection:
            customer_request_count_after_reset = connection.scalar(text("SELECT count(*) FROM customer_requests"))
            demo_request_count = connection.scalar(
                select(func.count(CustomerRequest.id)).where(CustomerRequest.id.in_(run["artifacts"]["customer_request_ids"]))
            )
        assert customer_request_count_after_reset == customer_request_count_before_reset
        assert demo_request_count == 2
    finally:
        engine.dispose()

    disabled_settings = Settings(demo_enabled=False)
    with TestClient(create_app(disabled_settings)) as disabled_client:
        disabled = disabled_client.post("/api/demo/runs", headers=admin_headers, json={})
    assert disabled.status_code == 404
    assert disabled.json()["code"] == "demo_unavailable"

    openapi = client.get("/openapi.json")
    assert {
        "/api/demo/runs",
        "/api/demo/runs/{demo_run_id}",
        "/api/demo/runs/{demo_run_id}/advance",
        "/api/demo/runs/{demo_run_id}/reset",
    }.issubset(set(openapi.json()["paths"]))
