from __future__ import annotations

import fnmatch
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
REQUIRED_FILES = [
    "VERSION",
    "CHANGELOG.md",
    "README.md",
    "docs/release/v0.1.0.md",
    "docs/release/release-checklist.md",
]
RISKY_TRACKED_PATTERNS = [
    ".env",
    ".env.local",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
    "frontend/dist",
    "frontend/dist/*",
    "frontend/node_modules",
    "frontend/node_modules/*",
    "*/__pycache__/*",
    "__pycache__/*",
    "*.pyc",
]
SECRET_EXAMPLES = [
    "DATABASE_URL=" + "postgresql://real",
    "OPENAI_API_KEY=" + "sk-",
    "BEGIN " + "PRIVATE KEY",
    "QUOTEOPS_" + "AUTH_SECRET=real",
]
RELEASE_COMMAND_MARKERS = [
    "gh " + "release create",
    "git " + "tag ",
    "git push origin v0.1.0",
]


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def main() -> int:
    results = [
        _check_required_files(),
        _check_version(),
        _check_changelog(),
        _check_release_docs(),
        _check_risky_tracked_files(),
        _check_release_docs_secret_safe(),
        _check_no_release_commands_in_script(),
    ]
    for result in results:
        prefix = "PASS" if result.passed else "FAIL"
        print(f"{prefix}: {result.name} - {result.detail}")
    return 0 if all(result.passed for result in results) else 1


def _check_required_files() -> CheckResult:
    missing = [path for path in REQUIRED_FILES if not (ROOT / path).exists()]
    return CheckResult(
        "required release package files",
        not missing,
        "all required files present" if not missing else f"missing: {', '.join(missing)}",
    )


def _check_version() -> CheckResult:
    path = ROOT / "VERSION"
    value = path.read_text(encoding="utf-8").strip() if path.exists() else ""
    return CheckResult("VERSION", value == VERSION, f"VERSION={value or 'missing'}")


def _check_changelog() -> CheckResult:
    path = ROOT / "CHANGELOG.md"
    text = _read_lower(path)
    required = [
        "v0.1.0",
        "portfolio-ready mvp release package",
        "no automatic price approval",
        "no automatic price table activation",
        "human review required before business use",
    ]
    missing = [item for item in required if item not in text]
    return CheckResult(
        "CHANGELOG.md v0.1.0 section",
        not missing,
        "v0.1.0 release notes present" if not missing else f"missing: {', '.join(missing)}",
    )


def _check_release_docs() -> CheckResult:
    combined = _read_lower(ROOT / "docs/release/v0.1.0.md") + "\n" + _read_lower(
        ROOT / "docs/release/release-checklist.md"
    )
    required = [
        "quoteops ai v0.1.0",
        "portfolio-ready mvp release package",
        "human review",
        "no automatic price approval",
        "no automatic price activation",
        "pr-35",
    ]
    missing = [item for item in required if item not in combined]
    return CheckResult(
        "release documentation",
        not missing,
        "release docs include boundaries and PR-35 plan" if not missing else f"missing: {', '.join(missing)}",
    )


def _check_risky_tracked_files() -> CheckResult:
    paths = _tracked_files()
    risky = [path for path in paths if _is_risky_tracked(path)]
    return CheckResult(
        "risky tracked files",
        not risky,
        "none found" if not risky else f"found: {', '.join(risky)}",
    )


def _check_release_docs_secret_safe() -> CheckResult:
    paths = [ROOT / "CHANGELOG.md", ROOT / "docs/release/v0.1.0.md", ROOT / "docs/release/release-checklist.md"]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths if path.exists()).lower()
    found = [example for example in SECRET_EXAMPLES if example.lower() in combined]
    return CheckResult(
        "release docs secret examples",
        not found,
        "no obvious real secret examples found" if not found else "forbidden secret-looking examples found",
    )


def _check_no_release_commands_in_script() -> CheckResult:
    text = (ROOT / "scripts/release_package_check.py").read_text(encoding="utf-8").lower()
    unsafe_calls = [
        "subprocess.run([" + '"git", "tag"',
        "subprocess.run([" + "'git', 'tag'",
        "subprocess.run([" + '"gh", "release"',
        "subprocess.run([" + "'gh', 'release'",
    ]
    unsafe = [call for call in unsafe_calls if call in text]
    return CheckResult(
        "no release command execution",
        not unsafe,
        "no tag or GitHub release command execution found" if not unsafe else f"unsafe calls: {', '.join(unsafe)}",
    )


def _tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def _is_risky_tracked(path: str) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in RISKY_TRACKED_PATTERNS)


def _read_lower(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").lower()


if __name__ == "__main__":
    sys.exit(main())
