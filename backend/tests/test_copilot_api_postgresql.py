from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from backend.config import Settings
from backend.db import build_engine, build_session_factory
from backend.domain.roles import UserRole
from backend.main import create_app
from backend.models.copilot_output import CopilotOutput
from backend.models.user import User
from backend.services.copilot import FailingCopilotProvider, StaticCopilotProvider, create_grounded_copilot_output
from backend.services.passwords import hash_password
from backend.schemas.copilot import GroundedCopilotOutputCreate

from test_html_report_api_postgresql import _approved_source, _token


pytestmark = pytest.mark.postgresql


def _truncate_copilot_workflow(engine) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE copilot_outputs, html_reports, approval_decisions, approval_requests, "
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
    settings = Settings()
    engine = build_engine(settings)
    try:
        _truncate_copilot_workflow(engine)
        session = build_session_factory(settings)()
        try:
            session.add_all(
                [
                    User(username="report-requester", display_name="Report Requester", password_hash=hash_password("report-requester-pass"), role=UserRole.MANAGER, active=True),
                    User(username="report-reviewer", display_name="Report Reviewer", password_hash=hash_password("report-reviewer-pass"), role=UserRole.MANAGER, active=True),
                    User(username="report-viewer", display_name="Report Viewer", password_hash=hash_password("report-viewer-pass"), role=UserRole.VIEWER, active=True),
                ]
            )
            session.commit()
        finally:
            session.close()
        with TestClient(create_app(settings)) as test_client:
            yield test_client
    finally:
        _truncate_copilot_workflow(engine)
        engine.dispose()


def _immutable_core_snapshot(engine) -> dict[str, list[dict[str, object]]]:
    statements = {
        "quotes": "SELECT id, status::text AS status, version, current_revision_number, total_amount::text AS total_amount FROM quotes ORDER BY id",
        "revisions": "SELECT id, quote_id, status::text AS status, revision_number, total_amount::text AS total_amount FROM quote_revisions ORDER BY id",
        "pricing": "SELECT id, quote_id, quote_revision_id, status::text AS status, selected_total_price::text AS selected_total_price FROM pricing_checks ORDER BY id",
        "approvals": "SELECT id, quote_id, status::text AS status, version, candidate_total_price::text AS candidate_total_price FROM approval_requests ORDER BY id",
        "reports": "SELECT id, quote_id, source_quote_revision_id, content_sha256 FROM html_reports ORDER BY id",
    }
    with engine.connect() as connection:
        return {name: [dict(row) for row in connection.execute(text(statement)).mappings()] for name, statement in statements.items()}


def _create_rejected_source(client: TestClient, requester_headers: dict[str, str], reviewer_headers: dict[str, str]) -> dict[str, object]:
    request = client.post(
        "/api/customer-requests",
        headers=requester_headers,
        json={"customer_name": "Rejected customer", "product_code": "a3_flyer", "quantity": 25},
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
        json={"request_version": reviewing.json()["version"], "title": "Rejected source"},
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
    rejected = client.post(
        f"/api/approval-requests/{pending.json()['id']}/reject",
        headers=reviewer_headers,
        json={"version": pending.json()["version"], "reason": "Revision needed before approval."},
    )
    assert rejected.status_code == 200
    return {"quote": quote.json(), "check": check.json(), "approval": rejected.json()}


def test_copilot_outputs_cover_grounded_contexts_without_mutating_core_evidence(client: TestClient) -> None:
    requester_headers = _token(client, "report-requester", "report-requester-pass")
    reviewer_headers = _token(client, "report-reviewer", "report-reviewer-pass")
    viewer_headers = _token(client, "report-viewer", "report-viewer-pass")
    source = _approved_source(client, requester_headers, reviewer_headers)
    approval = source["approval"]
    check = source["check"]
    quote = source["quote"]
    report_response = client.post(
        "/api/html-reports",
        headers=requester_headers,
        json={"approval_request_id": approval["id"], "title": "Grounded report"},
    )
    assert report_response.status_code == 201, report_response.text
    report = report_response.json()

    settings = Settings()
    engine = build_engine(settings)
    try:
        before = _immutable_core_snapshot(engine)
        assert client.post(f"/api/quotes/{quote['id']}/copilot-outputs", json={}).status_code == 401
        assert client.post(
            f"/api/quotes/{quote['id']}/copilot-outputs",
            headers=viewer_headers,
            json={"purpose": "candidate_explanation", "quote_revision_id": check["quote_revision_id"], "pricing_check_id": check["id"], "price_candidate_id": check["selected_candidate_id"]},
        ).status_code == 403

        pricing_payload = {"quote_revision_id": check["quote_revision_id"], "pricing_check_id": check["id"], "price_candidate_id": check["selected_candidate_id"]}
        outputs = []
        for purpose in ("candidate_explanation", "validation_summary", "approval_reason_draft"):
            response = client.post(
                f"/api/quotes/{quote['id']}/copilot-outputs",
                headers=requester_headers,
                json={"purpose": purpose, **pricing_payload},
            )
            assert response.status_code == 201, response.text
            outputs.append(response.json())
        report_output = client.post(
            f"/api/quotes/{quote['id']}/copilot-outputs",
            headers=requester_headers,
            json={"purpose": "report_summary_draft", "quote_revision_id": report["source_quote_revision_id"], "report_id": report["id"]},
        )
        assert report_output.status_code == 201, report_output.text
        outputs.append(report_output.json())

        for output in outputs:
            assert output["quote_id"] == quote["id"]
            assert output["generated_text"]
            assert output["deterministic_fallback"] is True
            assert output["generation_mode"] == "fallback"
            assert output["provider_name"] == "disabled"
            assert output["source_artifacts"]
            assert output["source_data_timestamp"]
            assert output["generated_at"]
            assert "material_cost" not in str(output).lower()
            assert "database_url" not in str(output).lower()
        detail = client.get(f"/api/copilot-outputs/{outputs[0]['id']}", headers=viewer_headers)
        assert detail.status_code == 200
        assert detail.json()["id"] == outputs[0]["id"]

        after = _immutable_core_snapshot(engine)
        assert after == before
        with engine.connect() as connection:
            actions = connection.execute(text("SELECT action FROM audit_events WHERE action = 'copilot_output.created' ORDER BY id")).scalars().all()
        assert len(actions) == 4
    finally:
        engine.dispose()

    openapi = client.get("/openapi.json")
    assert openapi.status_code == 200
    assert {"/api/quotes/{quote_id}/copilot-outputs", "/api/copilot-outputs/{output_id}"}.issubset(set(openapi.json()["paths"]))


def test_copilot_rejection_suggestion_provider_fixtures_and_output_immutability(client: TestClient) -> None:
    requester_headers = _token(client, "report-requester", "report-requester-pass")
    reviewer_headers = _token(client, "report-reviewer", "report-reviewer-pass")
    _approved_source(client, requester_headers, reviewer_headers)
    rejected_source = _create_rejected_source(client, requester_headers, reviewer_headers)
    approval = rejected_source["approval"]
    quote = rejected_source["quote"]
    response = client.post(
        f"/api/quotes/{quote['id']}/copilot-outputs",
        headers=requester_headers,
        json={
            "purpose": "rejection_revision_suggestion",
            "quote_revision_id": approval["decision"]["result_quote_revision_id"],
            "approval_request_id": approval["id"],
        },
    )
    assert response.status_code == 201, response.text
    output = response.json()
    assert output["purpose"] == "rejection_revision_suggestion"
    assert output["deterministic_fallback"] is True
    assert "새 draft revision" in output["generated_text"]

    settings = Settings()
    session = build_session_factory(settings)()
    try:
        actor = session.scalar(select(User).where(User.username == "report-requester"))
        assert actor is not None
        payload = GroundedCopilotOutputCreate(
            purpose="rejection_revision_suggestion",
            quote_revision_id=approval["decision"]["result_quote_revision_id"],
            approval_request_id=approval["id"],
        )
        successful = create_grounded_copilot_output(
            session,
            quote_id=quote["id"],
            payload=payload,
            actor=actor,
            request_id="static-provider-fixture",
            provider=StaticCopilotProvider("저장된 반려 근거를 검토하세요."),
        )
        assert successful.deterministic_fallback is False
        assert successful.generation_mode == "provider"
        assert successful.provider_name == "static_fixture"
        failed = create_grounded_copilot_output(
            session,
            quote_id=quote["id"],
            payload=payload,
            actor=actor,
            request_id="failing-provider-fixture",
            provider=FailingCopilotProvider("provider_timeout"),
        )
        assert failed.deterministic_fallback is True
        assert failed.provider_metadata["reason"] == "provider_timeout"
    finally:
        session.close()

    engine = build_engine(Settings())
    try:
        with engine.connect() as connection:
            with connection.begin():
                with pytest.raises(DBAPIError, match="copilot outputs are immutable"):
                    with connection.begin_nested():
                        connection.execute(text("UPDATE copilot_outputs SET generated_text = 'changed' WHERE id = :id"), {"id": output["id"]})
    finally:
        engine.dispose()


def test_copilot_rejects_mismatched_and_unsupported_provider_context(client: TestClient) -> None:
    requester_headers = _token(client, "report-requester", "report-requester-pass")
    reviewer_headers = _token(client, "report-reviewer", "report-reviewer-pass")
    source = _approved_source(client, requester_headers, reviewer_headers)
    check = source["check"]
    quote = source["quote"]
    bad = client.post(
        f"/api/quotes/{quote['id']}/copilot-outputs",
        headers=requester_headers,
        json={"purpose": "report_summary_draft", "quote_revision_id": check["quote_revision_id"]},
    )
    assert bad.status_code == 422
    assert bad.json()["code"] == "copilot_report_context_required"

    session = build_session_factory(Settings())()
    try:
        actor = session.scalar(select(User).where(User.username == "report-requester"))
        assert actor is not None
        fallback = create_grounded_copilot_output(
            session,
            quote_id=quote["id"],
            payload=GroundedCopilotOutputCreate(purpose="candidate_explanation", quote_revision_id=check["quote_revision_id"], pricing_check_id=check["id"], price_candidate_id=check["selected_candidate_id"]),
            actor=actor,
            request_id="malicious-provider-fixture",
            provider=StaticCopilotProvider("<script>unsupported</script>"),
        )
        assert fallback.deterministic_fallback is True
        assert fallback.provider_metadata["reason"] == "provider_output_unsupported"
    finally:
        session.close()
