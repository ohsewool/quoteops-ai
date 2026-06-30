import importlib.util
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "scripts" / "security_check.py"
RISKY_PATTERN = (
    r"(^\.env$|\.env\.local$|\.sqlite$|\.sqlite3$|quoteops\.db|"
    r"frontend/dist|frontend/node_modules|__pycache__|\.pyc$)"
)


def _load_security_check_module():
    spec = importlib.util.spec_from_file_location("security_check", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_security_check_script_exists():
    assert SCRIPT_PATH.exists()


def test_no_risky_generated_files_are_tracked():
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
    assert not any(path.startswith("frontend/dist/") for path in tracked)
    assert not any(path.startswith("frontend/node_modules/") for path in tracked)
    assert not any("__pycache__" in path for path in tracked)
    assert not any(path.endswith(".pyc") for path in tracked)
    assert not any(path.endswith((".db", ".sqlite", ".sqlite3")) for path in tracked)


def test_security_check_detects_no_findings_in_tracked_files():
    security_check = _load_security_check_module()

    assert security_check.run_check() == []


def test_security_check_secret_patterns_are_named_without_secret_values():
    security_check = _load_security_check_module()
    secret_value = "super-secret-password"

    for kind, pattern in security_check.SECRET_PATTERNS:
        assert secret_value not in kind
        assert pattern.pattern


def test_required_git_ls_files_pattern_is_documented_for_windows_equivalent():
    assert "frontend/node_modules" in RISKY_PATTERN
    assert r"quoteops\.db" in RISKY_PATTERN
