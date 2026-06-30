import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def test_readme_exists_and_mentions_quoteops_ai():
    text = _readme()

    assert README.exists()
    assert "# QuoteOps AI" in text
    assert "deterministic pricing-operations SaaS MVP" in text


def test_readme_includes_problem_and_solution_summary():
    text = _readme()

    assert "Problem Statement" in text
    assert "spreadsheets, manual reviews, and unclear approval processes" in text
    assert "Solution Overview" in text
    assert "centralizes quote operations" in text


def test_readme_mentions_deterministic_pricing_and_human_approval_boundary():
    text = _readme()

    assert "deterministic price calculations" in text
    assert "does not automatically approve prices" in text
    assert "does not automatically activate price tables" in text
    assert "Human review is required" in text


def test_readme_mentions_major_feature_groups():
    text = _readme()

    for feature in [
        "Product and cost profile management",
        "Quote preview",
        "Candidate price generation",
        "Price validation",
        "Human approval/rejection workflow",
        "Audit logs",
        "CSV import/export",
        "Pricing simulations",
        "Customer quote requests",
        "Price table history and comparison",
        "Workflow jobs",
        "Strategy templates",
        "KPI dashboard",
        "Dashboard insights",
        "Scenario comparisons",
        "HTML reports",
        "Render Deployed QA script",
        "Security and final regression checks",
    ]:
        assert feature in text


def test_readme_includes_local_setup_and_test_commands():
    text = _readme()

    for command in [
        "python -m venv .venv",
        "pip install -r requirements.txt",
        "uvicorn backend.main:app --reload",
        "cd frontend",
        "npm install",
        "npm run dev",
        "python -m compileall backend",
        "pytest -q",
        "npm run build",
        "python scripts/security_check.py",
        "python scripts/final_regression_check.py",
        "python scripts/render_deployed_qa.py",
    ]:
        assert command in text


def test_readme_documents_safe_environment_variables():
    text = _readme()

    for name in [
        "DATABASE_URL",
        "QUOTEOPS_ENV",
        "QUOTEOPS_AUTH_SECRET",
        "QUOTEOPS_DEMO_TOOLS_ENABLED",
        "QUOTEOPS_CORS_ORIGINS",
        "VITE_API_BASE_URL",
        "QUOTEOPS_DEPLOYED_BACKEND_URL",
        "QUOTEOPS_DEPLOYED_FRONTEND_URL",
    ]:
        assert name in text


def test_readme_contains_no_obvious_real_secrets():
    text = _readme()

    for forbidden in [
        "gho_",
        ("OPENAI_API_KEY=" + "sk-"),
        "postgresql://real-user:real-password@",
        ("BEGIN " + "PRIVATE KEY"),
        "super-secret-password",
    ]:
        assert forbidden not in text


def test_readme_does_not_claim_automatic_approval_or_activation():
    text = _readme().lower()

    assert "does not automatically approve" in text
    assert "does not automatically activate" in text
    assert "automatically approve prices." in text
    assert "automatically activate price tables" in text
    assert "automatically approves" not in text
    assert "automatically activates" not in text


def test_readme_links_only_to_existing_docs_files():
    text = _readme()
    linked_docs = re.findall(r"\]\((docs/[^)]+)\)", text)

    assert linked_docs
    for relative_path in linked_docs:
        assert (ROOT / relative_path).exists(), relative_path
