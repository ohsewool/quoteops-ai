import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"
FRONTEND_SOURCE = ROOT / "frontend" / "src"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_frontend_includes_core_workflow_korean_labels():
    source = _read(APP_SOURCE)

    for label in [
        "오늘의 작업",
        "고객 요청",
        "새 견적",
        "견적 미리보기",
        "가격 평가",
        "가격안 비교",
        "승인함",
        "승인 요청",
        "승인 대기",
        "승인 전 자동 반영 없음",
    ]:
        assert label in source


def test_frontend_includes_workflow_empty_and_error_copy():
    source = _read(APP_SOURCE)

    for text in [
        "아직 견적이 없습니다.",
        "첫 견적을 만들어 보세요.",
        "가격 평가",
        "현재 처리할 승인 항목이 없습니다.",
        "다시 불러오기",
        "데이터를 불러오지 못했습니다",
    ]:
        assert text in source


def test_frontend_keeps_all_major_navigation_sections_available():
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

    assert 'key: "simulations"' not in source


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
