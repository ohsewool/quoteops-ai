import sys
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.auth import require_role
from backend.db import create_db_and_tables
from backend.main import app
from backend.models import User
from backend.seed import seed_demo_data


client = TestClient(app)


def setup_module():
    create_db_and_tables()
    seed_demo_data()


def test_demo_admin_login_successfully():
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin-demo-password"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["username"] == "admin"
    assert data["user"]["role"] == "admin"


def test_login_fails_with_wrong_password():
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_me_returns_current_user_with_valid_token():
    token = _login("manager", "manager-demo-password")
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["username"] == "manager"
    assert response.json()["role"] == "manager"


def test_me_returns_401_with_invalid_token():
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401


def test_role_helper_allows_admin_where_required():
    dependency = require_role("admin")
    user = User(username="admin-test", display_name="Admin Test", role="admin", password_hash="x")

    assert dependency(user).role == "admin"


def test_role_helper_denies_viewer_where_manager_required():
    dependency = require_role("manager")
    user = User(username="viewer-test", display_name="Viewer Test", role="viewer", password_hash="x")

    with pytest.raises(HTTPException) as exc:
        dependency(user)
    assert exc.value.status_code == 403


def test_auth_responses_never_include_password_hash():
    token = _login("admin", "admin-demo-password")
    login_response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin-demo-password"},
    )
    me_response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    demo_response = client.get("/api/auth/demo-users")

    assert "password_hash" not in login_response.text
    assert "password_hash" not in me_response.text
    assert "password_hash" not in demo_response.text


def test_openapi_includes_auth_paths():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/auth/login" in paths
    assert "/api/auth/me" in paths


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
