import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import app


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_readme_exists_and_describes_current_project():
    text = read("README.md")

    assert "QuoteOps AI" in text
    assert "deterministic pricing-operations SaaS MVP" in text
    assert "Human review is required" in text
    assert "Quote preview" in text
    assert "Scenario comparisons" in text
    assert "Frontend navigation, loading, error, and empty state UX" in text


def test_readme_includes_local_run_and_test_commands():
    text = read("README.md")

    assert "python -m venv .venv" in text
    assert "pip install -r requirements.txt" in text
    assert "uvicorn backend.main:app --reload" in text
    assert "npm install" in text
    assert "npm run dev" in text
    assert "python -m compileall backend" in text
    assert "pytest -q" in text
    assert "npm run build" in text


def test_readme_mentions_required_environment_variables():
    text = read("README.md")

    for name in [
        "DATABASE_URL",
        "QUOTEOPS_ENV",
        "QUOTEOPS_AUTH_SECRET",
        "QUOTEOPS_DEMO_TOOLS_ENABLED",
        "QUOTEOPS_CORS_ORIGINS",
        "VITE_API_BASE_URL",
    ]:
        assert name in text


def test_deployment_docs_exist_and_include_render_commands():
    backend = read("docs/deployment/render-backend.md")
    frontend = read("docs/deployment/render-frontend.md")

    assert "pip install -r requirements.txt" in backend
    assert "uvicorn backend.main:app --host 0.0.0.0 --port $PORT" in backend
    assert "/api/health" in backend
    assert "QUOTEOPS_CORS_ORIGINS" in backend
    assert "cd frontend && npm install && npm run build" in frontend
    assert "frontend/dist" in frontend
    assert "VITE_API_BASE_URL" in frontend


def test_env_example_contains_safe_frontend_and_cors_values():
    text = read(".env.example")

    assert "DATABASE_URL=sqlite:///./quoteops.db" in text
    assert "QUOTEOPS_ENV=local" in text
    assert "QUOTEOPS_AUTH_SECRET=change-me-in-production" in text
    assert "QUOTEOPS_DEMO_TOOLS_ENABLED=true" in text
    assert "QUOTEOPS_CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173" in text
    assert "VITE_API_BASE_URL=http://127.0.0.1:8000" in text
    assert "https://YOUR-BACKEND-URL.onrender.com" in text
    assert "https://YOUR-FRONTEND-URL.onrender.com" in text


def test_docs_do_not_contain_obvious_real_secret_values():
    docs = [
        "README.md",
        ".env.example",
        "docs/DEPLOYMENT.md",
        "docs/deployment/render-backend.md",
        "docs/deployment/render-frontend.md",
        "docs/api-overview.md",
        "docs/demo-flow.md",
        "docs/safety-boundaries.md",
    ]
    combined = "\n".join(read(path) for path in docs).lower()

    for forbidden in [
        "gho_",
        "sk-",
        "raw-password",
        "password@example",
        "xoxb-",
    ]:
        assert forbidden not in combined


def test_api_overview_matches_representative_openapi_paths():
    text = read("docs/api-overview.md")
    client = TestClient(app)
    openapi_paths = client.get("/openapi.json").json()["paths"]

    for path in [
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
        "/api/pricing-simulations",
        "/api/customer-quote-requests",
        "/api/price-tables",
        "/api/workflow-jobs",
        "/api/strategy-templates",
        "/api/dashboard/summary",
        "/api/dashboard/insights",
        "/api/scenario-comparisons",
        "/api/html-reports",
        "/api/demo/status",
        "/api/demo/seed",
        "/api/demo/scenario/full",
        "/api/demo/guide",
    ]:
        assert path in text
        assert path in openapi_paths


def test_demo_and_safety_docs_include_boundaries():
    demo = read("docs/demo-flow.md")
    safety = read("docs/safety-boundaries.md")

    assert "No AI-generated price approval is performed" in demo
    assert "No price table is automatically activated" in demo
    assert "No external scraping is performed" in demo
    assert "Human approval is required" in safety
    assert "does not automatically approve prices" in safety
    assert "does not send emails" in safety


def test_openapi_still_loads():
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert len(response.json().get("paths", {})) > 20
