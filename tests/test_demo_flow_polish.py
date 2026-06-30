import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.main import app


DOCS = [
    ROOT / "docs" / "demo-flow.md",
    ROOT / "docs" / "demo-presenter-script.md",
    ROOT / "docs" / "demo-checklist.md",
    ROOT / "docs" / "demo-troubleshooting.md",
]
SCRIPT = ROOT / "scripts" / "demo_flow_check.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_demo_docs_exist():
    for path in DOCS:
        assert path.exists(), f"Missing demo doc: {path}"
        assert path.stat().st_size > 300


def test_demo_docs_cover_required_flow_and_safety_boundaries():
    combined = "\n".join(_read(path) for path in DOCS).lower()

    for phrase in [
        "customer quote request",
        "quote preview",
        "candidate prices",
        "price validation",
        "human review",
        "audit logs",
        "scenario comparison",
        "dashboard insights",
        "html report",
        "no ai-generated price approval",
        "no price table is automatically activated",
        "no quote is sent to a real customer",
        "no external scraping",
        "no payment or email",
    ]:
        assert phrase in combined


def test_demo_docs_do_not_contain_obvious_secrets():
    combined = "\n".join(_read(path).lower() for path in DOCS)

    forbidden = [
        "sk-",
        "gho_",
        "begin private key",
        "quoteops_" + "auth_secret=",
        "database_url=postgres",
        "password_hash",
    ]
    for term in forbidden:
        assert term not in combined


def test_readme_links_to_demo_docs():
    readme = _read(ROOT / "README.md")

    for link in [
        "docs/demo-flow.md",
        "docs/demo-presenter-script.md",
        "docs/demo-checklist.md",
        "docs/demo-troubleshooting.md",
    ]:
        assert link in readme


def test_demo_flow_script_exists_and_avoids_destructive_reset():
    assert SCRIPT.exists()
    text = _read(SCRIPT)

    assert "/api/demo/status" in text
    assert "/api/demo/guide" in text
    assert "/api/dashboard/summary" in text
    assert "/api/dashboard/insights" in text
    assert "POST /api/demo/reset" not in text
    assert 'post("/api/demo/reset"' not in text.lower()
    assert 'post("/api/demo/seed"' not in text.lower()


def test_demo_flow_script_runs_successfully():
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS: public demo readiness paths" in result.stdout
    assert "PASS: authenticated demo read paths" in result.stdout
    assert "PASS: openapi demo paths" in result.stdout
    assert "PASS: secret-safe demo responses" in result.stdout


def test_openapi_and_health_endpoints_still_work():
    client = TestClient(app)

    for path in ["/api/health", "/api/health/live", "/api/health/ready", "/openapi.json"]:
        response = client.get(path)
        assert response.status_code == 200
