from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

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


def _truncate_approval_workflow(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE approval_decisions, approval_requests, price_validation_checks, "
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
        _truncate_approval_workflow(engine)
        session = build_session_factory(settings)()
        try:
            session.add_all(
                [
                    User(
                        username="approval-requester",
                        display_name="Approval Requester",
                        password_hash=hash_password("approval-requester-pass"),
                        role=UserRole.MANAGER,
                        active=True,
                    ),
                    User(
                        username="approval-reviewer",
                        display_name="Approval Reviewer",
                        password_hash=hash_password("approval-reviewer-pass"),
                        role=UserRole.MANAGER,
                        active=True,
                    ),
                    User(
                        username="approval-reviewer-two",
                        display_name="Approval Reviewer Two",
                        password_hash=hash_password("approval-reviewer-two-pass"),
                        role=UserRole.MANAGER,
                        active=True,
                    ),
                    User(
                        username="approval-viewer",
                        display_name="Approval Viewer",
                        password_hash=hash_password("approval-viewer-pass"),
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
        _truncate_approval_workflow(engine)
        engine.dispose()


def _token(client: TestClient, username: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_quote(client: TestClient, manager_headers: dict[str, str], *, title: str) -> dict[str, object]:
    request = client.post(
        "/api/customer-requests",
        headers=manager_headers,
        json={
            "customer_name": title,
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
        json={"request_version": reviewing.json()["version"], "title": title},
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
        headers=manager_headers,
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
    return {"product_id": product.json()["id"]}


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
        headers=manager_headers,
        json={
            "quote_version": quote["version"],
            "quote_revision_id": quote["current_revision"]["id"],
            "selected_strategy": selected_strategy,
            "include_competitor_context": include_competitor_context,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _submit_approval(
    client: TestClient,
    manager_headers: dict[str, str],
    quote: dict[str, object],
    check: dict[str, object],
    *,
    reason: str | None = None,
):
    payload: dict[str, object] = {
        "quote_id": quote["id"],
        "pricing_check_id": check["id"],
        "price_candidate_id": check["selected_candidate_id"],
    }
    if reason is not None:
        payload["reason"] = reason
    return client.post("/api/approval-requests", headers=manager_headers, json=payload)


def test_approval_request_uses_immutable_evidence_and_separate_reviewer(client: TestClient) -> None:
    requester_headers = _token(client, "approval-requester", "approval-requester-pass")
    reviewer_headers = _token(client, "approval-reviewer", "approval-reviewer-pass")
    viewer_headers = _token(client, "approval-viewer", "approval-viewer-pass")
    _create_source_data(client, requester_headers)
    quote = _create_quote(client, requester_headers, title="Approval Happy Path")
    check = _create_pricing_check(client, requester_headers, quote)

    assert client.post("/api/approval-requests", json={}).status_code == 401
    assert client.post("/api/approval-requests", headers=viewer_headers, json={}).status_code == 403
    created = _submit_approval(client, requester_headers, quote, check)
    assert created.status_code == 201, created.text
    approval = created.json()
    assert approval["status"] == "pending"
    assert approval["quote_current_status"] == "approval_pending"
    assert approval["quote_revision_id"] == quote["current_revision"]["id"]
    assert approval["pricing_check_id"] == check["id"]
    assert approval["price_candidate_id"] == check["selected_candidate_id"]
    assert approval["validation_status"] == "passed"
    assert approval["risk_level"] == "low"
    assert approval["candidate_total_price"] == "76923.08"
    assert "material_cost" not in str(approval).lower()
    assert "cost_profile" not in str(approval).lower()

    own_decision = client.post(
        f"/api/approval-requests/{approval['id']}/approve",
        headers=requester_headers,
        json={"version": approval["version"]},
    )
    assert own_decision.status_code == 403
    assert own_decision.json()["code"] == "self_approval_prohibited"

    viewer_listing = client.get("/api/approval-requests", headers=viewer_headers)
    assert viewer_listing.status_code == 200
    assert viewer_listing.json()["total"] == 1
    assert viewer_listing.json()["items"][0]["id"] == approval["id"]

    approved = client.post(
        f"/api/approval-requests/{approval['id']}/approve",
        headers=reviewer_headers,
        json={"version": approval["version"], "reason": "Reviewed against saved evidence."},
    )
    assert approved.status_code == 200, approved.text
    decided = approved.json()
    assert decided["status"] == "approved"
    assert decided["quote_current_status"] == "approved"
    assert decided["version"] == 2
    assert decided["decision"]["decision"] == "approved"
    assert decided["decision"]["reviewer_user_id"] != decided["requester_user_id"]
    assert decided["decision"]["demo_self_approval_used"] is False

    repeated = client.post(
        f"/api/approval-requests/{approval['id']}/approve",
        headers=reviewer_headers,
        json={"version": decided["version"]},
    )
    assert repeated.status_code == 409
    assert repeated.json()["code"] == "approval_already_decided"

    settings = Settings()
    engine = build_engine(settings)
    try:
        with engine.connect() as connection:
            actions = connection.execute(
                text("SELECT action FROM audit_events ORDER BY id")
            ).scalars().all()
            audit_metadata = connection.execute(
                text("SELECT CAST(metadata_json AS TEXT) FROM audit_events WHERE action = 'approval_request.approved'")
            ).scalar_one().lower()
        assert "approval_request.created" in actions
        assert "approval_request.approved" in actions
        assert "password" not in audit_metadata
        assert "database_url" not in audit_metadata
        with engine.connect() as connection:
            with connection.begin():
                with pytest.raises(DBAPIError, match="approval request is terminal"):
                    with connection.begin_nested():
                        connection.execute(
                            text("UPDATE approval_requests SET status = 'rejected' WHERE id = :id"),
                            {"id": approval["id"]},
                        )
                with pytest.raises(DBAPIError, match="approval decisions are immutable"):
                    with connection.begin_nested():
                        connection.execute(
                            text("UPDATE approval_decisions SET reason = 'changed' WHERE approval_request_id = :id"),
                            {"id": approval["id"]},
                        )
    finally:
        engine.dispose()

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert {
        "/api/approval-requests",
        "/api/approval-requests/{approval_request_id}",
        "/api/approval-requests/{approval_request_id}/approve",
        "/api/approval-requests/{approval_request_id}/reject",
    }.issubset(set(openapi.json()["paths"]))


def test_approval_warning_blocked_and_rejection_creates_editable_revision(client: TestClient) -> None:
    requester_headers = _token(client, "approval-requester", "approval-requester-pass")
    reviewer_headers = _token(client, "approval-reviewer", "approval-reviewer-pass")
    source = _create_source_data(
        client,
        requester_headers,
        target_margin_rate="0.250000",
        reference_unit_price="10000.00",
    )
    warning_quote = _create_quote(client, requester_headers, title="Approval Warning")
    warning_check = _create_pricing_check(client, requester_headers, warning_quote)
    assert warning_check["status"] == "needs_review"
    no_reason = _submit_approval(client, requester_headers, warning_quote, warning_check)
    assert no_reason.status_code == 422
    assert no_reason.json()["code"] == "approval_reason_required"

    created = _submit_approval(
        client,
        requester_headers,
        warning_quote,
        warning_check,
        reason="The local relationship justifies review despite the market gap.",
    )
    assert created.status_code == 201, created.text
    approval = created.json()
    missing_rejection_reason = client.post(
        f"/api/approval-requests/{approval['id']}/reject",
        headers=reviewer_headers,
        json={"version": approval["version"], "reason": "   "},
    )
    assert missing_rejection_reason.status_code == 422
    assert missing_rejection_reason.json()["code"] == "rejection_reason_required"
    rejected = client.post(
        f"/api/approval-requests/{approval['id']}/reject",
        headers=reviewer_headers,
        json={"version": approval["version"], "reason": "Revise the margin before approval."},
    )
    assert rejected.status_code == 200, rejected.text
    rejected_payload = rejected.json()
    assert rejected_payload["status"] == "rejected"
    assert rejected_payload["quote_current_status"] == "draft"
    assert rejected_payload["decision"]["decision"] == "rejected"
    assert rejected_payload["decision"]["reason"] == "Revise the margin before approval."

    quote_after_rejection = client.get(f"/api/quotes/{warning_quote['id']}", headers=requester_headers)
    assert quote_after_rejection.status_code == 200
    revisions = client.get(f"/api/quotes/{warning_quote['id']}/revisions", headers=requester_headers)
    assert revisions.status_code == 200
    assert {item["status"] for item in revisions.json()["items"]}.issuperset({"approval_pending", "rejected", "draft"})
    revised_lines = client.put(
        f"/api/quotes/{warning_quote['id']}/lines",
        headers=requester_headers,
        json={
            "version": quote_after_rejection.json()["version"],
            "lines": [
                {
                    "description": "A3 Flyer revised after rejection",
                    "product_code": "a3_flyer",
                    "quantity": 25,
                    "unit_price": "100.00",
                }
            ],
        },
    )
    assert revised_lines.status_code == 200

    replacement_profile = client.post(
        "/api/cost-profiles",
        headers=requester_headers,
        json={
            "product_id": source["product_id"],
            "material_cost": "1000.00",
            "labor_cost": "500.00",
            "overhead_cost": "500.00",
            "target_margin_rate": "0.500000",
        },
    )
    assert replacement_profile.status_code == 201
    blocked_quote = _create_quote(client, requester_headers, title="Approval Blocked")
    blocked_check = _create_pricing_check(
        client,
        requester_headers,
        blocked_quote,
        selected_strategy="premium_margin",
        include_competitor_context=False,
    )
    assert blocked_check["status"] == "blocked"
    blocked = _submit_approval(client, requester_headers, blocked_quote, blocked_check)
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "blocked_pricing_check"


def test_two_reviewers_race_yields_exactly_one_terminal_decision(client: TestClient) -> None:
    requester_headers = _token(client, "approval-requester", "approval-requester-pass")
    reviewer_one_headers = _token(client, "approval-reviewer", "approval-reviewer-pass")
    reviewer_two_headers = _token(client, "approval-reviewer-two", "approval-reviewer-two-pass")
    _create_source_data(client, requester_headers)
    quote = _create_quote(client, requester_headers, title="Approval Race")
    check = _create_pricing_check(client, requester_headers, quote)
    created = _submit_approval(client, requester_headers, quote, check)
    assert created.status_code == 201
    approval = created.json()

    def approve(headers: dict[str, str]) -> tuple[int, str | None]:
        with TestClient(create_app(Settings())) as concurrent_client:
            response = concurrent_client.post(
                f"/api/approval-requests/{approval['id']}/approve",
                headers=headers,
                json={"version": approval["version"]},
            )
            return response.status_code, response.json().get("code")

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(approve, (reviewer_one_headers, reviewer_two_headers)))
    assert sorted(status_code for status_code, _ in results) == [200, 409]
    assert [code for status_code, code in results if status_code == 409] == ["approval_already_decided"]

    detail = client.get(f"/api/approval-requests/{approval['id']}", headers=requester_headers)
    assert detail.status_code == 200
    assert detail.json()["status"] == "approved"
    assert detail.json()["decision"] is not None
