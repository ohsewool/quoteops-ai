import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"
FRONTEND_SOURCE = ROOT / "frontend" / "src"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_frontend_includes_final_korean_copy_and_labels():
    source = _read(APP_SOURCE)

    for text in [
        "견적부터 승인까지 한 흐름으로",
        "견적 생성, 가격 평가, 승인, 리포트까지 한 번에 관리하세요.",
        "오늘 처리할 견적과 승인",
        "고객 요청 → 견적 생성 → 가격 평가 → 승인 → 리포트",
        "재료비",
        "인건비",
        "간접비",
        "목표 마진율",
        "고객명",
        "이메일",
        "회사명",
        "수량",
        "요청 메모",
        "승인 전 자동 반영 없음",
    ]:
        assert text in source


def test_internal_field_names_are_not_rendered_as_plain_visible_labels():
    source = _read(APP_SOURCE)

    for field in [
        "material_cost",
        "labor_cost",
        "overhead_cost",
        "target_margin_rate",
        "customer_name",
        "customer_email",
        "customer_company",
        "request_note",
    ]:
        assert f"<span>{{{field}}}</span>" not in source
        assert f"<span>{field}</span>" not in source


def test_home_status_hierarchy_keeps_only_high_value_status_cards():
    source = _read(APP_SOURCE)

    for label in [
        'label="서비스 정상"',
        'label="DB 연결 정상"',
        'label="OpenAPI 확인"',
        'label="배포 연결"',
    ]:
        assert label in source

    assert 'label="DB 유형"' not in source
    assert 'label="CORS"' not in source
    assert "lg:grid-cols-4" in source


def test_secondary_refresh_actions_use_secondary_button_style():
    source = _read(APP_SOURCE)

    assert 'primaryVariant: "secondary"' in source
    assert 'button compact secondary" onClick={refreshCustomerQuoteRequests}>다시 불러오기' in source
    assert 'button compact secondary" onClick={loadInitialData}' in source


def test_frontend_api_client_keeps_base_url_contract():
    source = _read(API_CLIENT_SOURCE)

    assert "VITE_API_BASE_URL" in source
    assert "http://127.0.0.1:8000" in source


def test_frontend_source_does_not_expose_backend_secret_names():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND_SOURCE.rglob("*") if path.is_file())

    assert "DATABASE_URL" not in combined
    assert "QUOTEOPS_AUTH_SECRET" not in combined


def test_generated_frontend_directories_are_not_tracked():
    result = subprocess.run(
        ["git", "ls-files", "frontend/dist", "frontend/node_modules"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == ""
