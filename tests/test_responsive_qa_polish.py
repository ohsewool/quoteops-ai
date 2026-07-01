import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"
CSS_SOURCE = ROOT / "frontend" / "src" / "styles.css"
CHECKLIST = ROOT / "docs" / "responsive-qa-checklist.md"
FRONTEND_SOURCE = ROOT / "frontend" / "src"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_responsive_qa_checklist_exists_with_required_topics():
    assert CHECKLIST.exists()
    text = _read(CHECKLIST).lower()

    for keyword in [
        "desktop",
        "laptop",
        "tablet",
        "mobile",
        "navigation",
        "cards",
        "forms",
        "buttons",
        "table-wrap",
        "가로 넘침",
        "render",
    ]:
        assert keyword in text


def test_frontend_css_keeps_required_responsive_breakpoints():
    css = _read(CSS_SOURCE)

    assert "min-width: 1200px" in css
    assert "min-width: 1024px" in css
    assert "min-width: 768px" in css
    assert "max-width: 767px" in css


def test_frontend_css_has_safe_responsive_layout_rules():
    css = _read(CSS_SOURCE)

    for expected in [
        ".app-nav-list",
        ".nav-pill",
        ".card-grid",
        ".status-grid",
        ".form-grid",
        ".table-wrap",
        ".overview-actions",
        ".workflow-layout",
        "grid-template-columns: 1fr",
        "overflow-x: auto",
        "overflow-x: hidden",
        "focus-visible",
        "white-space: normal",
    ]:
        assert expected in css


def test_frontend_source_still_exposes_all_major_navigation_labels():
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


def test_frontend_api_client_keeps_environment_base_url_contract():
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
