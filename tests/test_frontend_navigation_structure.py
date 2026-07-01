import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import app


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"


def _source() -> str:
    return APP_SOURCE.read_text(encoding="utf-8")


def _nav_source() -> str:
    source = _source()
    match = re.search(r"const NAV_SECTIONS = \[(.*?)\]\n\nconst", source, re.S)
    assert match, "NAV_SECTIONS should remain a simple static shell contract"
    return match.group(1)


def test_frontend_contains_cpq_workflow_navigation_labels():
    nav = _nav_source()

    expected_labels = [
        "대시보드",
        "고객 요청",
        "견적",
        "가격 평가",
        "승인함",
        "리포트",
        "운영",
        "데모",
    ]
    positions = [nav.index(f'label: "{label}"') for label in expected_labels]

    assert positions == sorted(positions)
    assert 'label: "시뮬레이션"' not in nav
    assert 'key: "simulations"' not in nav


def test_frontend_keeps_feature_sections_accessible_in_workflow_shell():
    source = _source()

    for text in [
        "시스템 상태",
        "견적 미리보기",
        "가격안",
        "가격 평가",
        "승인 대기 목록",
        "안전 설명",
        "감사 로그",
        "데이터 관리",
        "시뮬레이션",
        "고객 요청",
        "가격표 이력과 비교",
        "작업 상태",
        "전략 템플릿",
        "운영 요약",
        "분석 인사이트",
        "시나리오 비교",
        "리포트 생성",
        "데모",
    ]:
        assert text in source

    assert 'showSection("pricing-tools")' in source
    assert '<summary>시뮬레이션</summary>' in source
    assert 'showSection("admin-system")' in source


def test_frontend_overview_includes_safe_decision_boundary_and_quick_links():
    source = _source()

    assert "승인 전 자동 반영 없음" in source
    assert "승인 없이 가격을 확정하거나 전송하지 않습니다" in source
    assert "오늘의 작업" in source
    assert "고객 요청 → 견적 생성 → 가격 평가 → 승인 → 리포트" in source
    assert "견적 생성" in source
    assert "가격 평가" in source


def test_frontend_api_client_uses_vite_api_base_url_and_local_fallback():
    source = API_CLIENT_SOURCE.read_text(encoding="utf-8")

    assert "import.meta.env.VITE_API_BASE_URL" in source
    assert "http://127.0.0.1:8000" in source


def test_backend_openapi_still_loads():
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert "/api/health" in response.json()["paths"]
