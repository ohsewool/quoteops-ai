"""V2-10 release-readiness checks that do not need a deployed environment."""

from __future__ import annotations

from fastapi.testclient import TestClient

from backend.config import Environment, Settings
from backend.main import create_app


REQUIRED_V2_PATHS = {
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/auth/login",
    "/api/auth/me",
    "/api/customer-requests",
    "/api/customer-requests/{customer_request_id}",
    "/api/customer-requests/{customer_request_id}/transitions",
    "/api/customer-quote-requests/{customer_request_id}/quotes",
    "/api/quotes",
    "/api/quotes/{quote_id}",
    "/api/quotes/{quote_id}/lines",
    "/api/quotes/{quote_id}/pricing-checks",
    "/api/pricing-checks/{pricing_check_id}",
    "/api/approval-requests",
    "/api/approval-requests/{approval_request_id}/approve",
    "/api/approval-requests/{approval_request_id}/reject",
    "/api/html-reports",
    "/api/html-reports/{report_id}/content",
    "/api/quotes/{quote_id}/copilot-outputs",
    "/api/copilot-outputs/{output_id}",
    "/api/operations/diagnostics",
    "/api/operations/audit-events",
    "/api/operations/competitor-references/import",
    "/api/operations/competitor-references/export",
    "/api/demo/runs",
    "/api/demo/runs/{demo_run_id}/advance",
    "/api/demo/runs/{demo_run_id}/reset",
}

FROZEN_TIER_B_PATH_PREFIXES = (
    "/api/scenario",
    "/api/simulation",
    "/api/strategy-template",
    "/api/workflow-job",
    "/api/price-table",
)


class ReadySession:
    def execute(self, _statement: object) -> None:
        return None

    def close(self) -> None:
        return None


def _settings() -> Settings:
    return Settings(
        environment=Environment.TEST,
        database_url="postgresql+psycopg://release:password@localhost:5432/quoteops_v2",
        test_database_url="postgresql+psycopg://release_test:password@localhost:5432/quoteops_v2_test",
        auth_secret="release-readiness-test-secret",
        demo_enabled=False,
    )


def test_release_openapi_contract_contains_all_tier_a_v2_paths_and_no_frozen_tier_b_paths() -> None:
    app = create_app(_settings(), session_factory=ReadySession)
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = set(response.json()["paths"])
    assert REQUIRED_V2_PATHS.issubset(paths)
    assert not any(path.startswith(prefix) for path in paths for prefix in FROZEN_TIER_B_PATH_PREFIXES)


def test_release_public_health_contract_stays_sanitized_and_ready() -> None:
    app = create_app(_settings(), session_factory=ReadySession)
    with TestClient(app) as client:
        responses = [client.get(path) for path in ("/api/health", "/api/health/live", "/api/health/ready")]

    assert [response.status_code for response in responses] == [200, 200, 200]
    payload_text = "\n".join(response.text.lower() for response in responses)
    assert all(
        marker not in payload_text
        for marker in ("auth_secret", "database_url", "openai_api_key", "password", "begin private key")
    )
