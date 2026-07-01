import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"
FRONTEND_SOURCE = ROOT / "frontend" / "src"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_landing_copy_and_korean_display_labels_are_present():
    source = _read(APP_SOURCE)

    for text in [
        "견적부터 승인까지 한 흐름으로",
        "견적 생성, 가격 평가, 승인, 리포트까지 한 번에 관리하세요.",
        "서비스 시작하기",
        "데모 체험하기",
        "최종 가격은 승인 후 확정",
        "계산과 평가는 돕고, 결정은 사람이 합니다.",
        "고객명",
        "이메일",
        "회사명",
        "요청 메모",
        "재료비",
        "인건비",
        "간접비",
        "목표 마진율",
        "대기",
        "승인됨",
        "반려됨",
        "데이터를 불러오지 못했습니다.",
        "데모 매니저",
    ]:
        assert text in source


def test_old_landing_headline_and_common_english_ui_labels_are_not_visible_source():
    source = _read(APP_SOURCE)

    for text in [
        "견적 가격 운영의 시작점에서",
        "Demo Manager",
        "Customer Requests",
        "Candidate Prices",
        "Price Validation",
        "Approval Requests",
        "HTML Reports",
        "System Status",
        "Demo Tools",
        "MVP testing only",
    ]:
        assert text not in source


def test_display_mappings_keep_internal_keys_but_do_not_render_raw_labels():
    source = _read(APP_SOURCE)

    for internal_key in [
        "product_id",
        "customer_name",
        "customer_email",
        "customer_company",
        "request_note",
        "material_cost",
        "labor_cost",
        "overhead_cost",
        "target_margin_rate",
        "approval_status",
    ]:
        assert internal_key in source
        assert f"<span>{internal_key}</span>" not in source
        assert f"<th>{internal_key}</th>" not in source


def test_frontend_api_client_contract_and_secret_safety_remain_unchanged():
    api_source = _read(API_CLIENT_SOURCE)
    combined = "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND_SOURCE.rglob("*") if path.is_file())

    assert "VITE_API_BASE_URL" in api_source
    assert "http://127.0.0.1:8000" in api_source
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
