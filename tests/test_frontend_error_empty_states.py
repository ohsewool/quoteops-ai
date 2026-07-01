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

    assert "다시 시도" in source
    assert "백엔드에 연결할 수 없습니다." in source
    assert "로컬 백엔드 실행 상태 또는 배포 API URL을 확인하세요" in source


def test_frontend_contains_friendly_empty_state_copy_for_major_sections():
    source = APP_SOURCE.read_text(encoding="utf-8")

    for text in [
        "현재 처리할 승인 항목이 없습니다.",
        "아직 실행한 시나리오가 없습니다.",
        "아직 생성된 문서가 없습니다.",
        "등록된 고객 요청이 없습니다.",
        "표시할 요약 정보가 없습니다.",
        "아직 전략 템플릿이 없습니다.",
        "감사 로그가 없습니다.",
        "아직 견적이 없습니다.",
    ]:
        assert text in source


def test_frontend_contains_client_side_form_validation_copy():
    source = APP_SOURCE.read_text(encoding="utf-8")

    for text in [
        "상품을 선택한 뒤 가격 작업을 실행하세요.",
        "수량은 0보다 커야 합니다",
        "마진율은 0 이상 1 미만",
        "이메일 형식으로 입력하세요",
        "작업 입력값은 올바른 JSON이어야 합니다",
        "작업 제목을 입력하세요.",
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
