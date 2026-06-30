from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"


def test_frontend_api_client_keeps_env_base_url_contract():
    source = API_CLIENT_SOURCE.read_text(encoding="utf-8")

    assert "import.meta.env.VITE_API_BASE_URL" in source
    assert "http://127.0.0.1:8000" in source
    assert "axios.create" in source


def test_frontend_keeps_main_navigation_and_regression_ux_copy():
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
        "System Status",
        "Dashboard Insights",
        "Scenario Comparison",
        "HTML Reports",
    ]:
        assert label in source
    for text in [
        "Backend is not reachable",
        "Retry",
        "No approval requests yet",
        "No scenario comparisons yet",
        "No HTML reports yet",
        "No result yet",
    ]:
        assert text in source


def test_frontend_source_does_not_expose_backend_secret_names_or_keys():
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "frontend" / "src").rglob("*")
        if path.is_file() and path.suffix in {".js", ".jsx", ".css"}
    )

    for forbidden in [
        "DATABASE_URL",
        "QUOTEOPS_AUTH_SECRET",
        "OPENAI_API_KEY",
        "postgresql://",
        "sk-",
        ("BEGIN " + "PRIVATE KEY"),
    ]:
        assert forbidden not in combined


def test_deployment_config_and_docs_remain_present_and_placeholder_based():
    render_yaml = (ROOT / "render.yaml").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")
    backend_doc = (ROOT / "docs" / "deployment" / "render-backend.md").read_text(
        encoding="utf-8"
    )
    frontend_doc = (ROOT / "docs" / "deployment" / "render-frontend.md").read_text(
        encoding="utf-8"
    )

    assert "uvicorn backend.main:app" in render_yaml
    assert "--host 0.0.0.0" in render_yaml
    assert "--port $PORT" in render_yaml
    assert "healthCheckPath: /api/health" in render_yaml
    assert "sync: false" in render_yaml
    assert "VITE_API_BASE_URL" in env_example
    assert "QUOTEOPS_CORS_ORIGINS" in env_example
    assert "YOUR-BACKEND-URL" in env_example + frontend_doc
    assert "YOUR-FRONTEND-URL" in env_example + backend_doc
    assert "cd frontend && npm install && npm run build" in frontend_doc
    assert "frontend/dist" in frontend_doc
    for forbidden in ["gho_", "password@", ("OPENAI_API_KEY=" + "sk-"), "render.com/secret"]:
        assert forbidden not in render_yaml + env_example + backend_doc + frontend_doc
