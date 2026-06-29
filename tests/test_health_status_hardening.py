import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import app


client = TestClient(app)


def test_health_returns_200_without_secret_fields(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://demo:raw-password@example.com:5432/quoteops")
    monkeypatch.setenv("QUOTEOPS_AUTH_SECRET", "super-secret-auth-value")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value")

    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    body = response.text.lower()
    assert data["status"] == "ok"
    assert data["service"] == "quoteops-ai"
    assert "environment" in data
    assert "database_url" not in body
    assert "raw-password" not in body
    assert "auth_secret" not in body
    assert "openai_api_key" not in body
    assert "sk-secret-value" not in body


def test_health_live_returns_200_and_is_simple():
    response = client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json()["status"] == "alive"
    assert response.json()["service"] == "quoteops-ai"


def test_health_ready_returns_200_when_database_is_available():
    response = client.get("/api/health/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database_connection_ok"] is True
    assert data["database_type"] in {"sqlite", "postgresql", "other"}
    assert data["config_ok"] is True


def test_health_ready_returns_503_when_database_check_fails(monkeypatch):
    monkeypatch.setattr("backend.routers.health_api.database_connection_ok", lambda: False)

    response = client.get("/api/health/ready")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    assert data["database_connection_ok"] is False
    assert "database_url" not in response.text.lower()


def test_system_status_returns_nested_safe_operational_summary(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://demo:raw-password@example.com:5432/quoteops")
    monkeypatch.setenv("QUOTEOPS_AUTH_SECRET", "super-secret-auth-value")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret-value")

    response = client.get("/api/system/status")

    assert response.status_code == 200
    data = response.json()
    body = response.text.lower()
    assert data["service"] == "quoteops-ai"
    assert data["status"] in {"ok", "degraded"}
    assert "environment" in data
    assert data["database"]["configured"] is True
    assert data["database"]["type"] in {"sqlite", "postgresql", "other"}
    assert "connection_ok" in data["database"]
    assert data["cors"]["configured"] is True
    assert data["cors"]["origin_count"] >= 1
    assert data["cors"]["wildcard_enabled"] is False
    assert data["features"]["openapi_available"] is True
    assert data["security"]["secrets_exposed"] is False
    assert data["security"]["raw_db_url_exposed"] is False
    assert "database_url" not in body
    assert "raw-password" not in body
    assert "quoteops_auth_secret" not in body
    assert "auth_secret" not in body
    assert "openai_api_key" not in body
    assert "sk-secret-value" not in body


def test_system_status_handles_database_failure_without_secret_details(monkeypatch):
    monkeypatch.setattr("backend.routers.health_api.database_connection_ok", lambda: False)

    response = client.get("/api/system/status")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"]["connection_ok"] is False
    assert "database_url" not in response.text.lower()


def test_openapi_includes_health_and_status_endpoints():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/health" in paths
    assert "/api/health/live" in paths
    assert "/api/health/ready" in paths
    assert "/api/system/status" in paths


def test_readiness_check_does_not_modify_business_records(monkeypatch):
    calls = []

    def fake_database_connection_ok():
        calls.append("select_1")
        return True

    monkeypatch.setattr("backend.routers.health_api.database_connection_ok", fake_database_connection_ok)

    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert calls == ["select_1"]


def test_system_status_does_not_serialize_full_settings_object(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.health_api.get_settings",
        lambda: SimpleNamespace(
            database_url="postgresql://demo:raw-password@example.com:5432/quoteops",
            database_type="postgresql",
            environment="production",
            cors_origins_configured=True,
            cors_origin_count=1,
            cors_wildcard_enabled=False,
            openai_configured=True,
            demo_tools_enabled=False,
            auth_secret="must-not-appear",
        ),
    )
    monkeypatch.setattr("backend.routers.health_api.database_connection_ok", lambda: True)

    response = client.get("/api/system/status")

    body = response.text.lower()
    assert response.status_code == 200
    assert "raw-password" not in body
    assert "must-not-appear" not in body
    assert "auth_secret" not in body
