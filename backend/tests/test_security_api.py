from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from backend.api.dependencies import get_user_repository
from backend.config import Environment, Settings
from backend.domain.roles import UserRole
from backend.main import REQUEST_ID_HEADER, create_app
from backend.services.passwords import hash_password


@dataclass
class FakeUser:
    id: int
    username: str
    display_name: str
    password_hash: str
    role: UserRole
    active: bool = True


class FakeUserRepository:
    def __init__(self, users: list[FakeUser]) -> None:
        self.by_username = {user.username: user for user in users}
        self.by_id = {user.id: user for user in users}

    def get_by_username(self, username: str) -> FakeUser | None:
        return self.by_username.get(username)

    def get_active_by_id(self, user_id: int) -> FakeUser | None:
        user = self.by_id.get(user_id)
        return user if user and user.active else None


class ReadySession:
    def execute(self, _statement: object) -> None:
        return None

    def close(self) -> None:
        return None


class UnreadySession(ReadySession):
    def execute(self, _statement: object) -> None:
        raise SQLAlchemyError("database unavailable")


def settings(*, environment: Environment = Environment.TEST) -> Settings:
    return Settings(
        environment=environment,
        database_url="postgresql+psycopg://v2:password@localhost:5432/quoteops_v2",
        test_database_url="postgresql+psycopg://v2_test:password@localhost:5432/quoteops_v2_test",
        auth_secret="security-api-test-secret",
        docs_enabled=environment is not Environment.PRODUCTION,
        openapi_enabled=environment is not Environment.PRODUCTION,
    )


@pytest.fixture
def client() -> TestClient:
    password_hash = hash_password("correct-horse-battery-staple")
    repository = FakeUserRepository(
        [
            FakeUser(1, "admin", "Admin", password_hash, UserRole.ADMIN),
            FakeUser(2, "manager", "Manager", password_hash, UserRole.MANAGER),
            FakeUser(3, "viewer", "Viewer", password_hash, UserRole.VIEWER),
            FakeUser(4, "inactive", "Inactive", password_hash, UserRole.MANAGER, active=False),
        ]
    )
    app = create_app(settings(), session_factory=ReadySession)
    app.dependency_overrides[get_user_repository] = lambda: repository
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def login(client: TestClient, username: str) -> str:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": "correct-horse-battery-staple"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_only_contractual_foundation_routes_are_exposed(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert set(response.json()["paths"]) == {
        "/api/health",
        "/api/health/live",
        "/api/health/ready",
        "/api/auth/login",
        "/api/auth/me",
        "/api/system/status",
    }


def test_health_live_and_ready_are_public_and_correlated(client: TestClient) -> None:
    for path in ("/api/health", "/api/health/live", "/api/health/ready"):
        response = client.get(path, headers={REQUEST_ID_HEADER: "foundation-001"})
        assert response.status_code == 200
        assert response.headers[REQUEST_ID_HEADER] == "foundation-001"
        assert response.json()["status"] in {"ok", "ready"}


def test_readiness_returns_503_when_database_is_unavailable() -> None:
    app = create_app(settings(), session_factory=UnreadySession)
    with TestClient(app) as client:
        response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json()["code"] == "service_not_ready"


def test_login_me_and_inactive_user_behavior(client: TestClient) -> None:
    missing = client.post("/api/auth/login", json={"username": "missing", "password": "incorrect"})
    assert missing.status_code == 401
    assert missing.json()["code"] == "invalid_credentials"

    inactive = client.post(
        "/api/auth/login",
        json={"username": "inactive", "password": "correct-horse-battery-staple"},
    )
    assert inactive.status_code == 403
    assert inactive.json()["code"] == "inactive_user"

    no_token = client.get("/api/auth/me")
    assert no_token.status_code == 401
    assert no_token.json()["code"] == "authentication_required"

    malformed = client.post("/api/auth/login", json={"username": "x", "password": ""})
    assert malformed.status_code == 422
    assert malformed.json()["code"] == "validation_error"
    assert malformed.json()["field_errors"]
    assert malformed.json()["request_id"]

    response = client.get("/api/auth/me", headers=bearer(login(client, "manager")))
    assert response.status_code == 200
    assert response.json() == {
        "id": 2,
        "username": "manager",
        "display_name": "Manager",
        "role": "manager",
        "active": True,
    }


def test_system_status_is_admin_only_and_secret_safe(client: TestClient) -> None:
    anonymous = client.get("/api/system/status")
    assert anonymous.status_code == 401
    assert anonymous.json()["code"] == "authentication_required"

    viewer = client.get("/api/system/status", headers=bearer(login(client, "viewer")))
    assert viewer.status_code == 403
    assert viewer.json()["code"] == "permission_denied"

    admin = client.get("/api/system/status", headers=bearer(login(client, "admin")))
    assert admin.status_code == 200
    payload = admin.json()
    assert payload["environment"] == "test"
    assert "password" not in admin.text.lower()
    assert "postgresql" not in admin.text.lower()
    assert "secret" not in admin.text.lower()


def test_production_disables_docs_and_openapi() -> None:
    production_settings = settings(environment=Environment.PRODUCTION)
    app = create_app(production_settings, session_factory=ReadySession)
    with TestClient(app) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404
