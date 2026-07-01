import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import app


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"


def test_frontend_contains_reusable_loading_error_empty_components():
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "function LoadingState" in source
    assert "function ErrorState" in source
    assert "function EmptyState" in source
    assert "function FormErrorMessage" in source
    assert "function RetryButton" in source
    assert "function ResultPanel" in source


def test_frontend_contains_retry_and_backend_unavailable_copy():
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "Retry" in source
    assert "Backend is not reachable" in source
    assert "Start the backend locally or check the deployed API URL" in source


def test_frontend_contains_friendly_empty_state_copy_for_major_sections():
    source = APP_SOURCE.read_text(encoding="utf-8")

    for text_options in [
        ("No approval requests yet", "승인 대기 건이 없습니다."),
        ("No scenario comparisons yet", "아직 실행한 시나리오가 없습니다."),
        ("No HTML reports yet", "생성된 리포트가 없습니다."),
        ("No customer quote requests yet", "들어온 요청이 없습니다."),
        ("No workflow jobs yet", "시스템 운영 정보가 없습니다."),
        ("No strategy templates yet",),
        ("No audit logs loaded",),
        ("No result yet", "아직 견적이 없습니다."),
    ]:
        assert any(text in source for text in text_options)


def test_frontend_contains_client_side_form_validation_copy():
    source = APP_SOURCE.read_text(encoding="utf-8")

    for text in [
        "Choose a product",
        "Quantity must be greater than 0",
        "Margin rates must be numbers",
        "Customer email should look like an email address",
        "Input JSON must be valid JSON",
        "title cannot be empty",
    ]:
        assert text in source


def test_frontend_api_client_keeps_vite_base_url_and_local_fallback():
    source = API_CLIENT_SOURCE.read_text(encoding="utf-8")

    assert "import.meta.env.VITE_API_BASE_URL" in source
    assert "http://127.0.0.1:8000" in source
    assert "formatApiError" in source


def test_frontend_ui_source_does_not_render_raw_secret_names():
    source = APP_SOURCE.read_text(encoding="utf-8")

    for forbidden in [
        "DATABASE_URL",
        "QUOTEOPS_AUTH_SECRET",
        "OPENAI_API_KEY",
        "JWT secret",
        "private key",
    ]:
        assert forbidden not in source


def test_backend_health_status_and_openapi_still_load():
    client = TestClient(app)

    for path in [
        "/api/health",
        "/api/health/ready",
        "/api/system/status",
        "/openapi.json",
    ]:
        response = client.get(path)
        assert response.status_code == 200

    assert client.get("/openapi.json").json()["paths"]["/api/health"]
