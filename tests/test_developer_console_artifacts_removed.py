import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"
STYLES_SOURCE = ROOT / "frontend" / "src" / "styles.css"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_internal_codes_are_mapped_to_korean_labels_for_app_screens():
    source = _read(APP_SOURCE)

    for label in [
        "낮은 마진율",
        "기준 마진율",
        "프리미엄 마진율",
        "최소 마진 기준 충족",
        "로그인 완료",
        "승인됨",
        "반려됨",
        "검토 중",
        "데모 조회자",
        "고급 입력",
        "기술 정보",
        "샘플 데이터 준비",
        "가격 평가",
        "승인 처리",
        "리포트 확인",
        "관리자 모드",
        "매니저 모드",
        "조회자 모드",
    ]:
        assert label in source


def test_authenticated_header_uses_compact_user_chip_instead_of_role_card():
    source = _read(APP_SOURCE)
    styles = _read(STYLES_SOURCE)

    assert "user-chip" in source
    assert "displayRoleMode(currentUser.role)" in source
    assert "권한: {currentUser.role}" not in source
    assert "currentUser.role}</Badge>" not in source
    assert ".app-user-actions" in styles
    assert ".user-chip" in styles


def test_raw_codes_and_console_text_are_not_rendered_directly():
    source = _read(APP_SOURCE)

    for forbidden in [
        "{latestActions[0].action}",
        "<td>{log.action}</td>",
        "<td>{log.entity_type}</td>",
        "<td>{template.strategy_code}</td>",
        "<strong>{candidate.strategy}</strong>",
        '<h3 className="font-semibold">{candidate.strategy}</h3>',
        '<strong>{check.code}</strong> {check.passed ? "passed" : "needs review"}',
        ">Comparison is deterministic<",
        ">No AI-generated price was used.<",
    ]:
        assert forbidden not in source

    assert "displayAction(latestActions[0].action)" in source
    assert "displayAction(log.action)" in source
    assert "displayCode(log.entity_type)" in source
    assert "displayCode(template.strategy_code)" in source
    assert "displayCode(candidate.strategy)" in source
    assert "displayCode(check.code)" in source


def test_technical_status_and_json_inputs_are_disclosed_as_advanced_information():
    source = _read(APP_SOURCE)

    system_section_index = source.find('showSection("admin-system")')
    openapi_index = source.find('label="OpenAPI 확인"')

    assert system_section_index != -1
    assert openapi_index != -1
    assert system_section_index < openapi_index
    assert "advanced-details" in source
    assert "<summary>고급 입력</summary>" in source
    assert "<summary>기술 정보</summary>" in source
    assert "<span>입력 JSON</span>" in source


def test_frontend_api_contract_and_secret_safety_are_unchanged():
    api_source = _read(API_CLIENT_SOURCE)
    app_source = _read(APP_SOURCE)

    assert "import.meta.env.VITE_API_BASE_URL" in api_source
    assert "http://127.0.0.1:8000" in api_source
    assert "DATABASE_URL" not in app_source
    assert "QUOTEOPS_AUTH_SECRET" not in app_source


def test_generated_frontend_artifacts_are_not_tracked():
    result = subprocess.run(
        ["git", "ls-files", "frontend/dist", "frontend/node_modules"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    assert result.stdout.strip() == ""
