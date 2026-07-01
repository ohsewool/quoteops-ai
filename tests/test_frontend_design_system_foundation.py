import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"
CSS_SOURCE = ROOT / "frontend" / "src" / "styles.css"
FRONTEND_SOURCE = ROOT / "frontend" / "src"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_design_system_css_exists_with_core_tokens():
    assert CSS_SOURCE.exists()
    css = _read(CSS_SOURCE)

    for token in [
        "--color-bg",
        "--color-surface",
        "--color-primary",
        "--radius",
        "--shadow",
    ]:
        assert token in css


def test_design_system_has_responsive_breakpoints():
    css = _read(CSS_SOURCE)

    assert "@media (min-width: 1200px)" in css
    assert "@media (min-width: 1024px)" in css
    assert "@media (min-width: 768px)" in css
    assert "@media (max-width: 767px)" in css


def test_design_system_exposes_reusable_layout_classes():
    css = _read(CSS_SOURCE)

    for class_name in [
        ".app-shell",
        ".app-header",
        ".app-main",
        ".page-container",
        ".section",
        ".section-header",
        ".card",
        ".card-grid",
        ".status-grid",
        ".button",
        ".button-primary",
        ".button-secondary",
        ".button-ghost",
        ".badge",
        ".badge-success",
        ".badge-warning",
        ".badge-danger",
        ".form-grid",
        ".field",
        ".table-wrap",
        ".empty-state",
        ".error-state",
    ]:
        assert class_name in css


def test_frontend_keeps_major_workspace_sections_available():
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
    assert '<summary>시뮬레이션</summary>' in source


def test_frontend_api_client_uses_vite_base_url_and_local_fallback():
    source = _read(API_CLIENT_SOURCE)

    assert "VITE_API_BASE_URL" in source
    assert "http://127.0.0.1:8000" in source


def test_frontend_source_does_not_include_backend_secret_names():
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
