import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "render_deployed_qa.py"
DOC = ROOT / "docs" / "deployment" / "render-deployed-qa.md"
ENV_EXAMPLE = ROOT / ".env.example"


def test_render_deployed_qa_script_exists_and_has_main_entrypoint():
    source = SCRIPT.read_text(encoding="utf-8")

    assert SCRIPT.exists()
    assert "def main()" in source
    assert 'if __name__ == "__main__"' in source


def test_render_deployed_qa_script_uses_optional_url_env_vars():
    source = SCRIPT.read_text(encoding="utf-8")

    assert "QUOTEOPS_DEPLOYED_BACKEND_URL" in source
    assert "QUOTEOPS_DEPLOYED_FRONTEND_URL" in source
    assert "normalize_url" in source


def test_render_deployed_qa_script_uses_get_safe_endpoints_only():
    source = SCRIPT.read_text(encoding="utf-8")

    for path in [
        "/api/health",
        "/api/health/live",
        "/api/health/ready",
        "/api/system/status",
        "/openapi.json",
        "/api/dashboard/insights",
        "/api/demo/status",
        "/api/demo/guide",
    ]:
        assert path in source
    for forbidden in [
        "/api/demo/reset",
        "/api/demo/seed",
        "/api/demo/scenario/full",
        'method="POST"',
        "requests.",
    ]:
        assert forbidden not in source


def test_render_deployed_qa_script_checks_secret_safety_and_openapi():
    source = SCRIPT.read_text(encoding="utf-8").lower()

    assert "openapi.json" in source
    assert "path_count" in source
    for marker in [
        "database_url",
        "quoteops_auth_secret",
        "openai_api_key",
        "private key",
    ]:
        assert marker in source


def test_render_deployed_qa_script_skips_successfully_without_urls():
    env = {
        key: value
        for key, value in dict(**__import__("os").environ).items()
        if key
        not in {
            "QUOTEOPS_DEPLOYED_BACKEND_URL",
            "QUOTEOPS_DEPLOYED_FRONTEND_URL",
        }
    }
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "SKIP: deployed backend" in result.stdout
    assert "SKIP: deployed frontend" in result.stdout
    assert "SKIP: deployed CORS" in result.stdout


def test_render_deployed_qa_doc_exists_and_uses_placeholders_only():
    text = DOC.read_text(encoding="utf-8")

    assert DOC.exists()
    assert "This guide adds deployed QA support only" in text
    assert "QUOTEOPS_DEPLOYED_BACKEND_URL" in text
    assert "QUOTEOPS_DEPLOYED_FRONTEND_URL" in text
    assert "YOUR-BACKEND-URL" in text
    assert "YOUR-FRONTEND-URL" in text
    for forbidden in ["gho_", ("OPENAI_API_KEY=" + "sk-"), "real-password", ("BEGIN " + "PRIVATE KEY")]:
        assert forbidden not in text


def test_env_example_contains_optional_deployed_qa_placeholders():
    text = ENV_EXAMPLE.read_text(encoding="utf-8")

    assert "# QUOTEOPS_DEPLOYED_BACKEND_URL=https://YOUR-BACKEND-URL.onrender.com" in text
    assert "# QUOTEOPS_DEPLOYED_FRONTEND_URL=https://YOUR-FRONTEND-URL.onrender.com" in text


def test_readme_links_to_render_deployed_qa_doc():
    text = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Render Deployed QA" in text
    assert "python scripts/render_deployed_qa.py" in text
    assert "docs/deployment/render-deployed-qa.md" in text
