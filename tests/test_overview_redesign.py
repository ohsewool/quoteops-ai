import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"
FRONTEND_SOURCE = ROOT / "frontend" / "src"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_overview_includes_korean_hero_and_primary_actions():
    source = _read(APP_SOURCE)

    for text in [
        "견적부터 승인까지 한 흐름으로",
        "견적 생성, 가격 평가, 승인, 리포트까지 한 번에 관리하세요.",
        "계산, 원가, 승인, 리포트까지 한 흐름으로",
        "견적 시작",
        "데모 보기",
        "승인 전 자동 반영 없음",
    ]:
        assert text in source


def test_overview_includes_main_workflow_cards():
    source = _read(APP_SOURCE)

    for label in [
        "견적 생성",
        "가격 검증",
        "승인 관리",
        "리포트 생성",
    ]:
        assert label in source


def test_overview_keeps_demo_login_role_labels():
    source = _read(APP_SOURCE)

    for label in ["관리자", "매니저", "조회자", "로그인"]:
        assert label in source


def test_overview_keeps_all_major_navigation_sections_available():
    source = _read(APP_SOURCE)

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


def test_frontend_api_client_keeps_base_url_contract():
    source = _read(API_CLIENT_SOURCE)

    assert "VITE_API_BASE_URL" in source
    assert "http://127.0.0.1:8000" in source


def test_frontend_source_does_not_expose_backend_secret_names():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND_SOURCE.rglob("*") if path.is_file())

    assert "DATABASE_URL" not in combined
    assert "QUOTEOPS_AUTH_SECRET" not in combined


def test_frontend_build_outputs_are_not_tracked():
    result = subprocess.run(
        ["git", "ls-files", "frontend/dist", "frontend/node_modules"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == ""
