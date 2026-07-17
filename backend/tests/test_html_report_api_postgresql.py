from __future__ import annotations

import hashlib
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


def _truncate_report_workflow(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE html_reports, approval_decisions, approval_requests, price_validation_checks, "
                "price_validation_results, price_candidate_lines, price_candidates, pricing_checks, "
                "competitor_references, competitors, cost_profiles, products, quote_revision_lines, "
                "quote_revisions, quote_lines, quotes, audit_events, customer_requests, users "
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
        _truncate_report_workflow(engine)
        session = build_session_factory(settings)()
        try:
            session.add_all(
                [
                    User(
                        username="report-requester",
                        display_name="Report Requester",
                        password_hash=hash_password("report-requester-pass"),
                        role=UserRole.MANAGER,
                        active=True,
                    ),
                    User(
                        username="report-reviewer",
                        display_name="Report Reviewer",
                        password_hash=hash_password("report-reviewer-pass"),
                        role=UserRole.MANAGER,
                        active=True,
                    ),
                    User(
                        username="report-viewer",
                        display_name="Report Viewer",
                        password_hash=hash_password("report-viewer-pass"),
                        role=UserRole.VIEWER,
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
        _truncate_report_workflow(engine)
        engine.dispose()


def _token(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _approved_source(client: TestClient, requester_headers: dict[str, str], reviewer_headers: dict[str, str]) -> dict[str, object]:
    product = client.post(
        "/api/products",
        headers=requester_headers,
        json={"code": "a3_flyer", "name": "A3 Flyer", "description": "MVP product"},
    )
    assert product.status_code == 201
    cost_profile = client.post(
        "/api/cost-profiles",
        headers=requester_headers,
        json={
            "product_id": product.json()["id"],
            "material_cost": "1000.00",
            "labor_cost": "500.00",
            "overhead_cost": "500.00",
            "target_margin_rate": "0.350000",
        },
    )
    assert cost_profile.status_code == 201
    competitor = client.post(
        "/api/competitors",
        headers=requester_headers,
        json={"name": "Local Reference", "competitor_type": "local_shop"},
    )
    assert competitor.status_code == 201
    reference = client.post(
        "/api/competitor-references",
        headers=requester_headers,
        json={
            "competitor_id": competitor.json()["id"],
            "product_id": product.json()["id"],
            "quantity": 25,
            "price_basis": "unit_price",
            "reference_price": "3000.00",
            "observed_at": "2026-07-18T10:00:00Z",
        },
    )
    assert reference.status_code == 201
    request = client.post(
        "/api/customer-requests",
        headers=requester_headers,
        json={"customer_name": "<script>Customer</script>", "contact_name": "Kim", "product_code": "a3_flyer", "quantity": 25},
    )
    assert request.status_code == 201
    reviewing = client.post(
        f"/api/customer-requests/{request.json()['id']}/transitions",
        headers=requester_headers,
        json={"version": request.json()["version"], "target_status": "reviewing"},
    )
    assert reviewing.status_code == 200
    converted = client.post(
        f"/api/customer-quote-requests/{request.json()['id']}/quotes",
        headers=requester_headers,
        json={"request_version": reviewing.json()["version"], "title": "<script>Approved Quote</script>"},
    )
    assert converted.status_code == 201
    quote = converted.json()
    lines = client.put(
        f"/api/quotes/{quote['id']}/lines",
        headers=requester_headers,
        json={
            "version": quote["version"],
            "lines": [
                {
                    "description": "<script>line</script>",
                    "product_code": "a3_flyer",
                    "quantity": 25,
                    "unit_price": "0.00",
                }
            ],
        },
    )
    assert lines.status_code == 200
    quote = lines.json()
    pricing_check = client.post(
        f"/api/quotes/{quote['id']}/pricing-checks",
        headers=requester_headers,
        json={
            "quote_version": quote["version"],
            "quote_revision_id": quote["current_revision"]["id"],
            "selected_strategy": "target_margin",
            "include_competitor_context": True,
        },
    )
    assert pricing_check.status_code == 201, pricing_check.text
    check = pricing_check.json()
    approval = client.post(
        "/api/approval-requests",
        headers=requester_headers,
        json={
            "quote_id": quote["id"],
            "pricing_check_id": check["id"],
            "price_candidate_id": check["selected_candidate_id"],
        },
    )
    assert approval.status_code == 201, approval.text
    pending = approval.json()
    approved = client.post(
        f"/api/approval-requests/{pending['id']}/approve",
        headers=reviewer_headers,
        json={"version": pending["version"], "reason": "Independent review completed."},
    )
    assert approved.status_code == 200, approved.text
    return {"approval": approved.json(), "check": check, "quote": quote}


def test_html_report_is_grounded_in_approved_evidence_and_safe_for_viewers(client: TestClient) -> None:
    requester_headers = _token(client, "report-requester", "report-requester-pass")
    reviewer_headers = _token(client, "report-reviewer", "report-reviewer-pass")
    viewer_headers = _token(client, "report-viewer", "report-viewer-pass")
    source = _approved_source(client, requester_headers, reviewer_headers)
    approval = source["approval"]

    assert client.post("/api/html-reports", json={}).status_code == 401
    assert client.post(
        "/api/html-reports",
        headers=viewer_headers,
        json={"approval_request_id": approval["id"], "title": "Viewer attempt"},
    ).status_code == 403

    created = client.post(
        "/api/html-reports",
        headers=requester_headers,
        json={"approval_request_id": approval["id"], "title": "<script>Approved report</script>"},
    )
    assert created.status_code == 201, created.text
    report = created.json()
    assert report["source_quote_revision_id"] == approval["decision"]["result_quote_revision_id"]
    assert report["source_quote_status"] == "approved"
    assert report["approval_request_id"] == approval["id"]
    assert report["approval_decision_id"] == approval["decision"]["id"]
    assert report["candidate_total_price"] == approval["candidate_total_price"]
    assert report["candidate_gross_profit"] == approval["candidate_gross_profit"]
    assert report["candidate_margin_rate"] == approval["candidate_margin_rate"]
    assert report["validation_status"] == approval["validation_status"]
    assert report["risk_level"] == approval["risk_level"]
    assert report["predecessor_report_id"] is None
    assert len(report["lines"]) == 1
    assert "material_cost" not in str(report).lower()
    assert "labor_cost" not in str(report).lower()
    assert "overhead_cost" not in str(report).lower()

    viewer_list = client.get("/api/html-reports", headers=viewer_headers)
    assert viewer_list.status_code == 200
    assert viewer_list.json()[0]["id"] == report["id"]
    viewer_detail = client.get(f"/api/html-reports/{report['id']}", headers=viewer_headers)
    assert viewer_detail.status_code == 200
    assert viewer_detail.json()["content_sha256"] == report["content_sha256"]
    content = client.get(f"/api/html-reports/{report['id']}/content", headers=viewer_headers)
    assert content.status_code == 200
    assert content.headers["content-security-policy"].startswith("default-src 'none'")
    assert content.headers["x-content-type-options"] == "nosniff"
    assert "<script" not in content.text.lower()
    assert "&lt;script&gt;Approved report&lt;/script&gt;" in content.text
    assert "&lt;script&gt;Customer&lt;/script&gt;" in content.text
    assert hashlib.sha256(content.content).hexdigest() == report["content_sha256"]

    settings = Settings()
    engine = build_engine(settings)
    try:
        with engine.connect() as connection:
            actions = connection.execute(
                text("SELECT action FROM audit_events WHERE entity_type = 'html_report' ORDER BY id")
            ).scalars().all()
        with engine.connect() as connection:
            with connection.begin():
                with pytest.raises(DBAPIError, match="html reports are immutable"):
                    with connection.begin_nested():
                        connection.execute(
                            text("UPDATE html_reports SET title = 'changed' WHERE id = :id"),
                            {"id": report["id"]},
                        )
        assert {"html_report.created", "html_report.list_viewed", "html_report.viewed", "html_report.content_viewed"}.issubset(actions)
    finally:
        engine.dispose()

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert {
        "/api/html-reports",
        "/api/html-reports/{report_id}",
        "/api/html-reports/{report_id}/content",
    }.issubset(set(openapi.json()["paths"]))


def test_html_report_rejects_unapproved_source_and_preserves_regeneration_lineage(client: TestClient) -> None:
    requester_headers = _token(client, "report-requester", "report-requester-pass")
    reviewer_headers = _token(client, "report-reviewer", "report-reviewer-pass")

    product = client.post(
        "/api/products",
        headers=requester_headers,
        json={"code": "a3_flyer", "name": "A3 Flyer", "description": "MVP product"},
    )
    assert product.status_code == 201
    assert client.post(
        "/api/cost-profiles",
        headers=requester_headers,
        json={"product_id": product.json()["id"], "material_cost": "1000.00", "labor_cost": "500.00", "overhead_cost": "500.00", "target_margin_rate": "0.350000"},
    ).status_code == 201
    request = client.post(
        "/api/customer-requests",
        headers=requester_headers,
        json={"customer_name": "Pending customer", "product_code": "a3_flyer", "quantity": 25},
    )
    assert request.status_code == 201
    reviewing = client.post(
        f"/api/customer-requests/{request.json()['id']}/transitions",
        headers=requester_headers,
        json={"version": request.json()["version"], "target_status": "reviewing"},
    )
    assert reviewing.status_code == 200
    quote = client.post(
        f"/api/customer-quote-requests/{request.json()['id']}/quotes",
        headers=requester_headers,
        json={"request_version": reviewing.json()["version"], "title": "Pending source"},
    )
    assert quote.status_code == 201
    lines = client.put(
        f"/api/quotes/{quote.json()['id']}/lines",
        headers=requester_headers,
        json={"version": quote.json()["version"], "lines": [{"description": "A3", "product_code": "a3_flyer", "quantity": 25, "unit_price": "0.00"}]},
    )
    assert lines.status_code == 200
    check = client.post(
        f"/api/quotes/{quote.json()['id']}/pricing-checks",
        headers=requester_headers,
        json={"quote_version": lines.json()["version"], "quote_revision_id": lines.json()["current_revision"]["id"], "selected_strategy": "target_margin", "include_competitor_context": False},
    )
    assert check.status_code == 201
    pending = client.post(
        "/api/approval-requests",
        headers=requester_headers,
        json={"quote_id": quote.json()["id"], "pricing_check_id": check.json()["id"], "price_candidate_id": check.json()["selected_candidate_id"]},
    )
    assert pending.status_code == 201
    blocked = client.post(
        "/api/html-reports",
        headers=requester_headers,
        json={"approval_request_id": pending.json()["id"], "title": "Pending report"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "report_source_not_approved"

    approved = client.post(
        f"/api/approval-requests/{pending.json()['id']}/approve",
        headers=reviewer_headers,
        json={"version": pending.json()["version"], "reason": "Ready for report."},
    )
    assert approved.status_code == 200
    original = client.post(
        "/api/html-reports",
        headers=requester_headers,
        json={"approval_request_id": pending.json()["id"], "title": "Original report"},
    )
    assert original.status_code == 201
    regenerated = client.post(
        "/api/html-reports",
        headers=requester_headers,
        json={
            "approval_request_id": pending.json()["id"],
            "title": "Regenerated report",
            "predecessor_report_id": original.json()["id"],
        },
    )
    assert regenerated.status_code == 201, regenerated.text
    regenerated_payload = regenerated.json()
    assert regenerated_payload["predecessor_report_id"] == original.json()["id"]
    assert regenerated_payload["source_quote_revision_id"] == original.json()["source_quote_revision_id"]
    assert regenerated_payload["candidate_total_price"] == original.json()["candidate_total_price"]
    assert [item["id"] for item in regenerated_payload["regeneration_history"]] == [original.json()["id"], regenerated_payload["id"]]
    content = client.get(f"/api/html-reports/{regenerated_payload['id']}/content", headers=requester_headers)
    assert content.status_code == 200
    assert f"Regenerated from report #{original.json()['id']}" in content.text
