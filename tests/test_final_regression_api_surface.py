import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import app


client = TestClient(app)


REQUIRED_PATHS = [
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/system/status",
    "/api/quote-preview",
    "/api/candidate-prices",
    "/api/price-validation",
    "/api/approval-requests",
    "/api/explanations/quote",
    "/api/audit-logs",
    "/api/import/products",
    "/api/import/cost-profiles",
    "/api/import/competitor-prices",
    "/api/export/products.csv",
    "/api/export/cost-profiles.csv",
    "/api/export/competitor-prices.csv",
    "/api/pricing-simulations",
    "/api/customer-quote-requests",
    "/api/price-tables",
    "/api/price-table-snapshots/compare",
    "/api/workflow-jobs",
    "/api/strategy-templates",
    "/api/dashboard/summary",
    "/api/dashboard/metrics",
    "/api/dashboard/insights",
    "/api/dashboard/insights/rules",
    "/api/scenario-comparisons",
    "/api/html-reports",
    "/api/demo/status",
    "/api/demo/seed",
    "/api/demo/scenario/full",
    "/api/demo/guide",
]


def test_openapi_loads_and_contains_major_quoteops_api_surface():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    missing = [path for path in REQUIRED_PATHS if path not in paths]
    assert missing == []


def test_health_status_and_openapi_endpoints_return_safe_200_responses():
    for path in [
        "/api/health",
        "/api/health/live",
        "/api/health/ready",
        "/api/system/status",
        "/openapi.json",
    ]:
        response = client.get(path)
        assert response.status_code == 200


def test_health_and_status_responses_do_not_expose_secret_terms(monkeypatch):
    monkeypatch.setenv("QUOTEOPS_AUTH_SECRET", "super-secret-auth-value")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret-value")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://demo_user:" + "super-secret-password" + "@example.com:5432/demo",
    )

    combined = (
        client.get("/api/health").text.lower()
        + client.get("/api/health/live").text.lower()
        + client.get("/api/health/ready").text.lower()
        + client.get("/api/system/status").text.lower()
    )

    for forbidden in [
        "database_url",
        "quoteops_auth_secret",
        "auth_secret",
        "openai_api_key",
        "sk-test",
        "super-secret-password",
        "super-secret-auth-value",
        ("begin " + "private key"),
    ]:
        assert forbidden not in combined


def test_api_surface_documents_actual_import_export_aliases():
    docs = Path("docs/api-overview.md").read_text(encoding="utf-8")

    assert "/api/import/products" in docs
    assert "/api/export/products.csv" in docs
    assert "not under a single `/api/csv` prefix" in docs
