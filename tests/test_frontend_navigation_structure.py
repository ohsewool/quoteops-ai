import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import app


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"


def test_frontend_contains_main_navigation_labels():
    source = APP_SOURCE.read_text(encoding="utf-8")

    for label in [
        "Overview",
        "Quote Operations",
        "Pricing Tools",
        "Approvals",
        "Customer Requests",
        "Simulations",
        "Reports",
        "Admin / System",
        "Demo Tools",
    ]:
        assert label in source


def test_frontend_keeps_existing_feature_sections_accessible():
    source = APP_SOURCE.read_text(encoding="utf-8")

    for label in [
        "System Status",
        "Quote Preview",
        "Candidate Prices",
        "Price Validation",
        "Approval Requests",
        "Safe Explanation",
        "Audit Logs",
        "CSV Import and Export",
        "Pricing Simulation",
        "Customer Quote Requests",
        "Price Table History and Comparison",
        "Workflow Jobs",
        "Strategy Templates",
        "KPI Dashboard",
        "Dashboard Insights",
        "Scenario Comparison",
        "HTML Reports",
        "Demo Tools",
    ]:
        assert label in source


def test_frontend_overview_includes_safe_decision_boundary_and_quick_links():
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "Safe pricing decision boundary" in source
    assert "does not automatically approve, activate, or send prices" in source
    assert "Quick links" in source


def test_frontend_api_client_uses_vite_api_base_url_and_local_fallback():
    source = API_CLIENT_SOURCE.read_text(encoding="utf-8")

    assert "import.meta.env.VITE_API_BASE_URL" in source
    assert "http://127.0.0.1:8000" in source


def test_backend_openapi_still_loads():
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/health" in response.json()["paths"]
