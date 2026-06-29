import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import app


client = TestClient(app)


def test_system_status_does_not_return_raw_database_password(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.health_api.get_settings",
        lambda: SimpleNamespace(
            database_url="postgresql://demo:raw-password@example.com:5432/quoteops",
            database_type="postgresql",
            openai_configured=False,
            demo_tools_enabled=True,
        ),
    )
    monkeypatch.setattr("backend.routers.health_api.database_connection_ok", lambda: True)

    response = client.get("/api/system/status")

    assert response.status_code == 200
    body = response.text
    data = response.json()
    assert data["database_type"] == "postgresql"
    assert data["database_connection_ok"] is True
    assert "database_url_safe" not in data
    assert "raw-password" not in body
    assert "demo:raw-password" not in body
    assert "database_url" not in body


def test_health_does_not_return_raw_database_password(monkeypatch):
    monkeypatch.setattr(
        "backend.routers.health_api.get_settings",
        lambda: SimpleNamespace(
            database_url="postgresql://demo:raw-password@example.com:5432/quoteops",
            database_type="postgresql",
            openai_configured=False,
            demo_tools_enabled=True,
        ),
    )
    monkeypatch.setattr("backend.routers.health_api.database_connection_ok", lambda: True)

    response = client.get("/api/health")

    assert response.status_code == 200
    body = response.text
    data = response.json()
    assert data["database_type"] == "postgresql"
    assert data["database_connection_ok"] is True
    assert "raw-password" not in body
    assert "postgresql://demo" not in body
