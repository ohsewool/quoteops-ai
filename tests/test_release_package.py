import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.main import app


VERSION = ROOT / "VERSION"
CHANGELOG = ROOT / "CHANGELOG.md"
RELEASE_NOTES = ROOT / "docs" / "release" / "v0.1.0.md"
RELEASE_CHECKLIST = ROOT / "docs" / "release" / "release-checklist.md"
RELEASE_SCRIPT = ROOT / "scripts" / "release_package_check.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_version_file_exists_and_is_exact():
    assert VERSION.exists()
    assert _read(VERSION) == "0.1.0\n"


def test_changelog_exists_and_contains_v0_1_0():
    assert CHANGELOG.exists()
    text = _read(CHANGELOG).lower()

    assert "v0.1.0" in text
    assert "portfolio-ready mvp release package" in text


def test_release_docs_exist():
    assert RELEASE_NOTES.exists()
    assert RELEASE_CHECKLIST.exists()


def test_release_docs_include_human_review_and_no_auto_boundaries():
    combined = (_read(CHANGELOG) + "\n" + _read(RELEASE_NOTES) + "\n" + _read(RELEASE_CHECKLIST)).lower()

    for phrase in [
        "human review",
        "no automatic price approval",
        "no automatic price table activation",
        "no automatic price activation",
        "no real competitor scraping",
        "no email sending",
        "no payment flow",
    ]:
        assert phrase in combined


def test_release_docs_do_not_claim_production_or_autonomous_ai():
    combined = (_read(CHANGELOG) + "\n" + _read(RELEASE_NOTES)).lower()

    forbidden = [
        "production-ready enterprise platform",
        "fully autonomous ai pricing engine",
        "real-time market scraping",
        "automatic customer quote sending",
    ]
    for phrase in forbidden:
        assert phrase not in combined


def test_release_package_script_exists_and_does_not_execute_release_commands():
    assert RELEASE_SCRIPT.exists()
    text = _read(RELEASE_SCRIPT).lower()

    assert "subprocess.run([\"git\", \"tag\"" not in text
    assert "subprocess.run(['git', 'tag'" not in text
    assert "subprocess.run([\"gh\", \"release\"" not in text
    assert "subprocess.run(['gh', 'release'" not in text


def test_release_package_script_passes():
    result = subprocess.run(
        [sys.executable, str(RELEASE_SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS: VERSION" in result.stdout
    assert "PASS: release documentation" in result.stdout
    assert "PASS: no release command execution" in result.stdout


def test_readme_links_to_release_docs():
    text = _read(ROOT / "README.md")

    assert "## Release Status" in text
    assert "docs/release/v0.1.0.md" in text
    assert "docs/release/release-checklist.md" in text
    assert "GitHub Release are handled separately" in text


def test_openapi_still_loads():
    client = TestClient(app)
    response = client.get("/openapi.json")

    assert response.status_code == 200
