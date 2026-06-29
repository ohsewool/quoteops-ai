import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import app


ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_render_yaml_exists():
    assert _render_yaml_path().exists()


def test_render_yaml_contains_backend_web_service():
    text = _render_yaml()

    assert "type: web" in text
    assert "name: quoteops-ai-backend" in text
    assert "runtime: python" in text


def test_render_yaml_build_command_installs_requirements():
    text = _render_yaml()

    assert "buildCommand: pip install -r requirements.txt" in text


def test_render_yaml_start_command_uses_uvicorn_backend_main():
    text = _render_yaml()

    assert "uvicorn backend.main:app" in text


def test_render_yaml_start_command_binds_to_render_host_and_port():
    text = _render_yaml()

    assert "--host 0.0.0.0" in text
    assert "--port $PORT" in text


def test_render_yaml_health_check_path_is_api_health():
    text = _render_yaml()

    assert "healthCheckPath: /api/health" in text


def test_render_yaml_does_not_contain_obvious_secret_values():
    text = _render_yaml().lower()

    forbidden = ["postgresql://", "postgres://", "gho_", "sk-", "password@", "render.com/"]
    assert not any(value in text for value in forbidden)
    assert "sync: false" in text


def test_env_example_exists():
    assert (ROOT / ".env.example").exists()


def test_env_example_does_not_contain_real_credentials():
    text = (ROOT / ".env.example").read_text(encoding="utf-8").lower()

    assert "database_url=sqlite:///./quoteops.db" in text
    assert "# database_url=postgresql://user:password@host:5432/dbname" in text
    assert "gho_" not in text
    assert "sk-" not in text
    assert "render.com" not in text


def test_gitignore_ignores_env_and_sqlite_files():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert ".env" in text
    assert ".env.local" in text
    assert "quoteops.db" in text
    assert "quoteops_audit_tmp.db" in text
    assert "*.sqlite" in text
    assert "*.sqlite3" in text


def test_health_endpoint_works_with_testclient():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["service"] == "quoteops-ai"


def test_system_status_does_not_expose_raw_database_password(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.health_api.get_settings",
        lambda: SimpleNamespace(
            database_url="postgresql://demo:raw-password@example.com:5432/quoteops",
            database_type="postgresql",
            database_url_safe="postgresql://***:***@example.com:5432/quoteops",
            database_connection_ok=True,
            environment="production",
            openai_configured=False,
            demo_tools_enabled=False,
        ),
    )
    monkeypatch.setattr("backend.routers.health_api.database_connection_ok", lambda: True)

    response = client.get("/api/system/status")

    assert response.status_code == 200
    text = response.text.lower()
    assert "raw-password" not in text
    assert "demo:raw-password" not in text
    assert response.json()["environment"] == "production"


def test_openapi_still_loads():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/health" in response.json()["paths"]


def _render_yaml_path() -> Path:
    return ROOT / "render.yaml"


def _render_yaml() -> str:
    return _render_yaml_path().read_text(encoding="utf-8")
