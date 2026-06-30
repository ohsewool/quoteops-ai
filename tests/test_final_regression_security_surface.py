import importlib.util
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import create_db_and_tables
from backend.main import app
from backend.seed import seed_demo_data


ROOT = Path(__file__).resolve().parents[1]
SECURITY_SCRIPT = ROOT / "scripts" / "security_check.py"
client = TestClient(app)


def setup_module():
    create_db_and_tables()
    seed_demo_data()


def test_security_check_script_still_passes_for_tracked_files():
    security_check = _load_security_check()

    assert security_check.run_check() == []


def test_no_risky_generated_files_are_tracked_in_final_regression():
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    tracked = [line.strip().replace("\\", "/") for line in result.stdout.splitlines()]

    assert ".env" not in tracked
    assert ".env.local" not in tracked
    assert "quoteops.db" not in tracked
    assert "quoteops_audit_tmp.db" not in tracked
    assert not any(path.endswith((".db", ".sqlite", ".sqlite3", ".pyc")) for path in tracked)
    assert not any(path.startswith("frontend/dist/") for path in tracked)
    assert not any(path.startswith("frontend/node_modules/") for path in tracked)
    assert not any("__pycache__" in path for path in tracked)


def test_html_report_escapes_user_controlled_title_in_final_regression():
    title = "<script>alert(&quot;xss&quot;)</script>"
    response = client.post(
        "/api/html-reports",
        headers=_auth_headers("manager"),
        json={"report_type": "dashboard_summary", "title": title},
    )

    assert response.status_code == 201
    content = client.get(
        f"/api/html-reports/{response.json()['id']}/content",
        headers=_auth_headers("viewer"),
    )
    assert content.status_code == 200
    assert "<script>" not in content.text
    assert "&lt;script&gt;" in content.text


def test_demo_reset_safety_doc_and_endpoint_do_not_claim_global_reset():
    guide = client.get("/api/demo/guide", headers=_auth_headers("viewer"))
    checklist = (ROOT / "docs" / "security-checklist.md").read_text(encoding="utf-8")

    assert guide.status_code == 200
    assert "Demo tools do not approve, reject, or activate production prices." in guide.text
    assert "demo reset" in checklist.lower()
    assert "known deterministic demo data" in checklist


def test_docs_and_examples_have_no_obvious_real_secret_values():
    checked = [
        ROOT / "README.md",
        ROOT / ".env.example",
        ROOT / "render.yaml",
        *list((ROOT / "docs").rglob("*.md")),
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in checked)

    assert "YOUR-BACKEND-URL" in combined
    assert "YOUR-FRONTEND-URL" in combined
    for forbidden in [
        "gho_",
        ("OPENAI_API_KEY=" + "sk-"),
        ("DATABASE_URL=" + "postgresql://real-user:real-password@"),
        ("BEGIN " + "PRIVATE KEY"),
        "super-secret-password",
    ]:
        assert forbidden not in combined


def _load_security_check():
    spec = importlib.util.spec_from_file_location("security_check", SECURITY_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _auth_headers(username: str) -> dict:
    token = _login(username, f"{username}-demo-password")
    return {"Authorization": f"Bearer {token}"}


def _login(username: str, password: str) -> str:
    response = client.post("/api/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]
