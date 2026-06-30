from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    "frontend/dist",
    "frontend/node_modules",
}
RISKY_TRACKED_PATTERNS = [
    re.compile(r"^\.env$"),
    re.compile(r"^\.env\.local$"),
    re.compile(r"(^|/).*\.db$"),
    re.compile(r"(^|/).*\.sqlite$"),
    re.compile(r"(^|/).*\.sqlite3$"),
    re.compile(r"^quoteops\.db$"),
    re.compile(r"^quoteops_audit_tmp\.db$"),
    re.compile(r"^frontend/dist(/|$)"),
    re.compile(r"^frontend/node_modules(/|$)"),
    re.compile(r"(^|/)__pycache__(/|$)"),
    re.compile(r"(^|/).*\.pyc$"),
]
SECRET_PATTERNS = [
    (
        "database_url_with_credentials",
        re.compile(
            r"\bDATABASE_URL\s*=\s*postgres(?:ql)?(?:\+\w+)?://"
            r"(?!USER:PASSWORD@)(?!user:password@)[^:\s/@]+:[^@\s]+@",
            re.IGNORECASE,
        ),
    ),
    (
        "quoteops_auth_secret_literal",
        re.compile(
            r"\bQUOTEOPS_AUTH_SECRET\s*=\s*"
            r"(?!change-me-in-production\b)(?!change-me\b)(?!YOUR_)[^\s#]+",
            re.IGNORECASE,
        ),
    ),
    (
        "openai_api_key_literal",
        re.compile(r"\bOPENAI_API_KEY\s*=\s*sk-[A-Za-z0-9_-]+", re.IGNORECASE),
    ),
    ("private_key_block", re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY")),
    (
        "real_password_assignment",
        re.compile(r"\bpassword\s*=\s*real-password\b", re.IGNORECASE),
    ),
]
SAFE_LINE_MARKERS = {
    "USER:PASSWORD",
    "user:password",
    "change-me-in-production",
    "YOUR-BACKEND-URL",
    "YOUR-FRONTEND-URL",
    "sqlite:///./quoteops.db",
    "sk-secret-value",
    "sk-test-secret-value",
}


@dataclass(frozen=True)
class Finding:
    path: str
    kind: str


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def risky_tracked_findings(paths: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        normalized = path.replace("\\", "/")
        if any(pattern.search(normalized) for pattern in RISKY_TRACKED_PATTERNS):
            findings.append(Finding(path=path, kind="risky_tracked_file"))
    return findings


def secret_findings(paths: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        normalized = path.replace("\\", "/")
        if _should_skip(normalized):
            continue
        content = _read_text_if_possible(ROOT / path)
        if content is None:
            continue
        for line in content.splitlines():
            if _is_safe_placeholder_line(line):
                continue
            for kind, pattern in SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(Finding(path=path, kind=kind))
                    break
    return findings


def run_check() -> list[Finding]:
    paths = tracked_files()
    return risky_tracked_findings(paths) + secret_findings(paths)


def main() -> int:
    findings = run_check()
    if findings:
        print("Security check failed:")
        for finding in findings:
            print(f"- {finding.path}: {finding.kind}")
        return 1
    print("Security check passed: no obvious tracked secrets or risky generated files found.")
    return 0


def _should_skip(path: str) -> bool:
    return any(path == part or path.startswith(f"{part}/") for part in SKIP_PARTS)


def _read_text_if_possible(path: Path) -> str | None:
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\x00" in data:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _is_safe_placeholder_line(line: str) -> bool:
    return any(marker in line for marker in SAFE_LINE_MARKERS)


if __name__ == "__main__":
    sys.exit(main())
