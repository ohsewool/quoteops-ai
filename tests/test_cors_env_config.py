import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import DEFAULT_CORS_ORIGINS, get_cors_origins
from backend.main import app


client = TestClient(app)
REPO_ROOT = Path(__file__).resolve().parents[1]


def test_local_default_cors_origins_include_dev_frontends(monkeypatch):
    monkeypatch.delenv("QUOTEOPS_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    origins = get_cors_origins(environment="local")

    assert origins == DEFAULT_CORS_ORIGINS
    assert "http://localhost:5173" in origins
    assert "http://127.0.0.1:5173" in origins
    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3000" in origins
    assert "*" not in origins


def test_comma_separated_cors_origins_parse_in_order():
    origins = get_cors_origins(
        "https://frontend.example.com,http://localhost:5173",
        environment="production",
    )

    assert origins == ["https://frontend.example.com", "http://localhost:5173"]


def test_cors_origin_whitespace_empty_values_and_duplicates_are_removed():
    origins = get_cors_origins(
        " https://frontend.example.com, ,http://localhost:5173,"
        "https://frontend.example.com,, ",
        environment="local",
    )

    assert origins == ["https://frontend.example.com", "http://localhost:5173"]


def test_production_environment_does_not_default_to_wildcard(monkeypatch):
    monkeypatch.delenv("QUOTEOPS_CORS_ORIGINS", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)

    assert "*" not in get_cors_origins(environment="production")
    assert get_cors_origins("*", environment="production") == []


def test_fastapi_app_includes_cors_middleware():
    assert any(
        middleware.cls.__name__ == "CORSMiddleware" for middleware in app.user_middleware
    )


def test_health_returns_200():
    response = client.get("/api/health")

    assert response.status_code == 200


def test_system_status_returns_safe_config_fields(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://demo:raw-password@example.com:5432/quoteops")
    monkeypatch.setenv("QUOTEOPS_AUTH_SECRET", "super-secret-auth-value")

    response = client.get("/api/system/status")

    assert response.status_code == 200
    body = response.text
    data = response.json()
    assert data["service"] == "quoteops-ai"
    assert "environment" in data
    assert data["cors_origins_configured"] is True
    assert data["cors_origin_count"] >= 1
    assert "raw-password" not in body
    assert "super-secret-auth-value" not in body
    assert "database_url" not in body
    assert "quoteops_auth_secret" not in body.lower()
    assert "auth_secret" not in body.lower()


def test_env_example_contains_safe_cors_and_frontend_api_examples():
    env_example = (REPO_ROOT / ".env.example").read_text(encoding="utf-8")

    assert "QUOTEOPS_CORS_ORIGINS=" in env_example
    assert "VITE_API_BASE_URL=http://127.0.0.1:8000" in env_example
    assert "YOUR-BACKEND-URL.onrender.com" in env_example
    assert "YOUR-FRONTEND-URL.onrender.com" in env_example
    assert "raw-password" not in env_example
    assert "sk-" not in env_example


def test_frontend_api_client_uses_vite_api_base_url_with_local_fallback():
    client_js = (REPO_ROOT / "frontend" / "src" / "api" / "client.js").read_text(
        encoding="utf-8"
    )

    assert "import.meta.env.VITE_API_BASE_URL" in client_js
    assert "http://127.0.0.1:8000" in client_js


def test_openapi_still_loads():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/health" in response.json()["paths"]
