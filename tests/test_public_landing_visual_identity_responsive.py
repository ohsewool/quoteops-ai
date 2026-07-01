import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"
CSS_SOURCE = ROOT / "frontend" / "src" / "styles.css"
FRONTEND_SOURCE = ROOT / "frontend" / "src"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_public_landing_includes_service_entry_copy():
    source = _read(APP_SOURCE)

    for text in [
        "견적 가격 운영의 시작점에서",
        "서비스 시작하기",
        "데모 체험하기",
        "로그인",
        "승인 전 자동 반영 없음",
        "포트폴리오 데모용 계정",
        "견적 생성",
        "가격 평가",
        "승인 관리",
        "리포트 생성",
    ]:
        assert text in source


def test_authenticated_navigation_labels_remain_available():
    source = _read(APP_SOURCE)

    for section_key in [
        "overview",
        "quote-operations",
        "pricing-tools",
        "approvals",
        "customer-requests",
        "simulations",
        "reports",
        "admin-system",
        "demo-tools",
    ]:
        assert f'key: "{section_key}"' in source

    assert source.count("label:") >= 9


def test_source_has_public_landing_and_authenticated_shell_modes():
    source = _read(APP_SOURCE)

    assert "if (!currentUser)" in source
    assert "public-shell" in source
    assert "public-hero" in source
    assert "public-entry-card" in source
    assert "app-nav-list" in source
    assert source.find("public-shell") < source.find("app-nav-list")


def test_css_has_visual_identity_tokens_and_landing_classes():
    css = _read(CSS_SOURCE)

    for expected in [
        "#fe7902",
        "#292929",
        "#fffff5",
        ".public-shell",
        ".public-hero",
        ".public-flow-card",
        ".public-cta",
        ".public-entry-card",
        "@media (min-width: 1200px)",
        "@media (min-width: 1024px)",
        "@media (min-width: 768px)",
        "@media (max-width: 767px)",
    ]:
        assert expected in css


def test_css_has_responsive_rules_for_public_and_authenticated_layouts():
    css = _read(CSS_SOURCE)

    for expected in [
        ".public-flow-section",
        ".public-cta-row",
        ".public-demo-grid",
        ".app-nav-list",
        ".workflow-layout",
        "grid-template-columns: 1fr",
    ]:
        assert expected in css


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
