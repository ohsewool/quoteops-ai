import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_SOURCE = ROOT / "frontend" / "src" / "App.jsx"
API_CLIENT_SOURCE = ROOT / "frontend" / "src" / "api" / "client.js"
FRONTEND_SOURCE = ROOT / "frontend" / "src"
PORTFOLIO_QA = ROOT / "docs" / "portfolio-ui-qa.md"
README = ROOT / "README.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_portfolio_ui_qa_doc_exists_with_final_qa_topics():
    assert PORTFOLIO_QA.exists()
    text = _read(PORTFOLIO_QA)

    for keyword in [
        "PR-42",
        "포트폴리오 시연 흐름",
        "Render 재배포",
        "홈",
        "견적",
        "가격",
        "승인",
        "시뮬레이션",
        "리포트",
        "운영",
        "데모",
        "승인 전 자동 반영 없음",
        "https://quoteops-ai-frontend.onrender.com",
        "https://quoteops-ai-backend.onrender.com/api/health",
        "scripts/render_deployed_qa.py",
    ]:
        assert keyword in text


def test_readme_includes_concise_live_demo_section():
    text = _read(README)

    for keyword in [
        "## Live Demo",
        "https://quoteops-ai-frontend.onrender.com",
        "https://quoteops-ai-backend.onrender.com/api/health",
        "https://quoteops-ai-backend.onrender.com/openapi.json",
        "portfolio SaaS MVP",
        "does not automatically approve",
    ]:
        assert keyword in text


def test_frontend_source_keeps_final_portfolio_ui_contract():
    source = _read(APP_SOURCE)

    for keyword in [
        "견적부터 승인까지 한 흐름으로",
        "견적 생성, 가격 평가, 승인, 리포트까지 한 번에 관리하세요.",
        "승인 전 자동 반영 없음",
        "overview",
        "quote-operations",
        "pricing-tools",
        "approvals",
        "simulations",
        "reports",
        "admin-system",
        "demo-tools",
    ]:
        assert keyword in source


def test_frontend_api_client_keeps_deployable_base_url_contract():
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
