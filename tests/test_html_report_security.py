import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import create_db_and_tables
from backend.main import app
from backend.seed import seed_demo_data


client = TestClient(app)


def setup_module():
    create_db_and_tables()
    seed_demo_data()


def test_html_report_escapes_script_tags_in_user_controlled_title():
    payload = {
        "report_type": "dashboard_summary",
        "title": '<script>alert("xss")</script>',
    }
    create_response = client.post(
        "/api/html-reports",
        headers=_auth_headers("manager"),
        json=payload,
    )

    assert create_response.status_code == 201
    report_id = create_response.json()["id"]
    content_response = client.get(
        f"/api/html-reports/{report_id}/content",
        headers=_auth_headers("viewer"),
    )

    assert content_response.status_code == 200
    assert '<script>alert("xss")</script>' not in content_response.text
    assert "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;" in content_response.text


def test_html_report_content_uses_no_external_scripts_or_remote_assets():
    create_response = client.post(
        "/api/html-reports",
        headers=_auth_headers("manager"),
        json={"report_type": "dashboard_summary", "title": "Security report"},
    )
    report_id = create_response.json()["id"]
    content_response = client.get(
        f"/api/html-reports/{report_id}/content",
        headers=_auth_headers("viewer"),
    )
    lowered = content_response.text.lower()

    assert "<script" not in lowered
    assert "https://" not in lowered
    assert "http://" not in lowered


def _auth_headers(username: str) -> dict:
    token = _login(username, f"{username}-demo-password")
    return {"Authorization": f"Bearer {token}"}


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
