import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import app


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"


def test_frontend_contains_main_navigation_labels():
    source = APP_SOURCE.read_text(encoding="utf-8")

    for label_options in [
        ("Overview", "홈"),
        ("Quote Operations", "견적"),
        ("Pricing Tools", "가격"),
        ("Approvals", "승인"),
        ("Customer Requests", "고객 요청"),
        ("Simulations", "시뮬레이션"),
        ("Reports", "리포트"),
        ("Admin / System", "운영"),
        ("Demo Tools", "데모"),
    ]:
        assert any(label in source for label in label_options)


def test_frontend_keeps_existing_feature_sections_accessible():
    source = APP_SOURCE.read_text(encoding="utf-8")

    for label_options in [
        ("System Status",),
        ("Quote Preview", "견적 미리보기"),
        ("Candidate Prices", "가격안"),
        ("Price Validation", "가격 평가"),
        ("Approval Requests", "승인 관리"),
        ("Safe Explanation", "안전 설명"),
        ("Audit Logs",),
        ("CSV Import and Export",),
        ("Pricing Simulation",),
        ("Customer Quote Requests", "고객 요청"),
        ("Price Table History and Comparison",),
        ("Workflow Jobs",),
        ("Strategy Templates",),
        ("KPI Dashboard",),
        ("Dashboard Insights",),
        ("Scenario Comparison",),
        ("HTML Reports",),
        ("Demo Tools",),
    ]:
        assert any(label in source for label in label_options)


def test_frontend_overview_includes_safe_decision_boundary_and_quick_links():
    source = APP_SOURCE.read_text(encoding="utf-8")

    assert "승인 전 자동 반영 없음" in source
    assert "승인 없이 가격을 확정하거나 전송하지 않습니다" in source
    assert "주요 흐름" in source
    assert "견적 생성" in source
    assert "가격 검증" in source


def test_frontend_api_client_uses_vite_api_base_url_and_local_fallback():
    source = API_CLIENT_SOURCE.read_text(encoding="utf-8")

    assert "import.meta.env.VITE_API_BASE_URL" in source
    assert "http://127.0.0.1:8000" in source


def test_backend_openapi_still_loads():
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/health" in response.json()["paths"]
