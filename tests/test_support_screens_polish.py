import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"
FRONTEND_SOURCE = ROOT / "frontend" / "src"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_frontend_includes_support_screen_korean_labels():
    source = _read(APP_SOURCE)

    for label in [
        "운영 요약",
        "분석 인사이트",
        "시뮬레이션",
        "시나리오 비교",
        "리포트",
        "리포트 생성",
        "운영",
        "시스템 상태",
        "데이터 가져오기",
        "작업 상태",
        "데모",
        "데모 시작",
        "샘플 불러오기",
    ]:
        assert label in source


def test_frontend_includes_support_screen_empty_and_error_copy():
    source = _read(APP_SOURCE)

    for text in [
        "표시할 요약 정보가 없습니다.",
        "아직 실행한 시나리오가 없습니다.",
        "아직 생성된 문서가 없습니다.",
        "데모 상태",
        "다시 불러오기",
    ]:
        assert text in source


def test_frontend_keeps_all_major_navigation_labels_available():
    source = _read(APP_SOURCE)

    for label in [
        "대시보드",
        "고객 요청",
        "견적",
        "가격 평가",
        "승인함",
        "리포트",
        "운영",
        "데모",
    ]:
        assert label in source

    assert 'label: "시뮬레이션"' not in source


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
