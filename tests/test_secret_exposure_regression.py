import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.config import get_cors_origins
from backend.main import app


ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)
PRIVATE_KEY_MARKER = "BEGIN " + "PRIVATE KEY"
POSTGRES_SECRET_URL = (
    "postgresql://demo_user:"
    + "super-secret-password"
    + "@example.com:5432/demo"
)
DANGEROUS_VALUES = [
    POSTGRES_SECRET_URL,
    "super-secret-password",
    "super-secret-auth-value",
    "sk-test-secret-value",
    PRIVATE_KEY_MARKER,
]


def test_health_and_status_endpoints_do_not_expose_raw_secrets(monkeypatch):
    monkeypatch.setenv(
        "DATABASE_URL",
        POSTGRES_SECRET_URL,
    )
    monkeypatch.setenv("QUOTEOPS_AUTH_SECRET", "super-secret-auth-value")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-secret-value")

    combined = "".join(
        client.get(path).text.lower()
        for path in [
            "/api/health",
            "/api/health/live",
            "/api/health/ready",
            "/api/system/status",
        ]
    )

    for forbidden in [
        "database_url",
        "quoteops_auth_secret",
        "auth_secret",
        "openai_api_key",
        "sk-test-secret-value",
        "super-secret-password",
        "super-secret-auth-value",
        ("begin " + "private key"),
    ]:
        assert forbidden not in combined


def test_production_cors_removes_wildcard_and_dedupes_origins():
    origins = get_cors_origins(
        "*, https://frontend.example.com, ,https://frontend.example.com",
        environment="production",
    )

    assert origins == ["https://frontend.example.com"]


def test_frontend_source_does_not_contain_backend_secrets_or_real_production_urls():
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (ROOT / "frontend" / "src").rglob("*")
        if path.is_file() and path.suffix in {".js", ".jsx", ".css"}
    )

    assert "import.meta.env.VITE_API_BASE_URL" in source
    assert "http://127.0.0.1:8000" in source
    for forbidden in [
        "DATABASE_URL",
        "QUOTEOPS_AUTH_SECRET",
        "OPENAI_API_KEY",
        "sk-",
        "postgresql://",
        "render.com",
    ]:
        assert forbidden not in source


def test_deployment_docs_and_examples_use_placeholders_only():
    checked_paths = [
        ROOT / "render.yaml",
        ROOT / ".env.example",
        ROOT / "README.md",
        *list((ROOT / "docs").rglob("*.md")),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in checked_paths)

    assert "YOUR-BACKEND-URL" in combined
    assert "YOUR-FRONTEND-URL" in combined
    for forbidden in DANGEROUS_VALUES:
        assert forbidden not in combined
    assert ("OPENAI_API_KEY=" + "sk-") not in combined
    assert ("DATABASE_URL=" + "postgresql://real-user:real-password@") not in combined


def test_openapi_loads_without_secret_examples():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    body = response.text.lower()
    for forbidden in [
        "quoteops_auth_secret",
        "openai_api_key",
        "super-secret",
        "sk-test",
        ("begin " + "private key"),
    ]:
        assert forbidden not in body
