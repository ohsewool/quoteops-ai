from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.db import create_db_and_tables
from backend.main import app
from backend.seed import seed_demo_data


client = TestClient(app)

PUBLIC_PATHS = [
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/system/status",
    "/openapi.json",
]
AUTHENTICATED_READ_PATHS = [
    "/api/demo/status",
    "/api/demo/guide",
    "/api/dashboard/summary",
    "/api/dashboard/insights",
]
FORBIDDEN_TERMS = [
    "database_url",
    "quoteops_auth_secret",
    "auth_secret",
    "openai_api_key",
    "password_hash",
    "access_token",
    "begin private key",
]


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


def main() -> int:
    create_db_and_tables()
    seed_demo_data()
    results = [
        _check_public_paths(),
        _check_authenticated_read_paths(),
        _check_openapi_loaded(),
        _check_secret_safe_responses(),
    ]
    for result in results:
        prefix = "PASS" if result.passed else "FAIL"
        print(f"{prefix}: {result.name} - {result.detail}")
    return 0 if all(result.passed for result in results) else 1


def _check_public_paths() -> CheckResult:
    statuses = {path: client.get(path).status_code for path in PUBLIC_PATHS}
    passed = all(status == 200 for status in statuses.values())
    return CheckResult("public demo readiness paths", passed, _format_statuses(statuses))


def _check_authenticated_read_paths() -> CheckResult:
    headers = _auth_headers("viewer")
    statuses = {path: client.get(path, headers=headers).status_code for path in AUTHENTICATED_READ_PATHS}
    passed = all(status == 200 for status in statuses.values())
    return CheckResult("authenticated demo read paths", passed, _format_statuses(statuses))


def _check_openapi_loaded() -> CheckResult:
    response = client.get("/openapi.json")
    paths = response.json().get("paths", {}) if response.status_code == 200 else {}
    required_paths = [path for path in PUBLIC_PATHS if path != "/openapi.json"] + AUTHENTICATED_READ_PATHS
    missing = [path for path in required_paths if path not in paths]
    return CheckResult(
        "openapi demo paths",
        response.status_code == 200 and not missing,
        "all demo paths present" if not missing else f"missing: {', '.join(missing)}",
    )


def _check_secret_safe_responses() -> CheckResult:
    headers = _auth_headers("viewer")
    public_text = "".join(
        client.get(path).text.lower() for path in PUBLIC_PATHS if path != "/openapi.json"
    )
    read_text = "".join(client.get(path, headers=headers).text.lower() for path in AUTHENTICATED_READ_PATHS)
    found = [term for term in FORBIDDEN_TERMS if term in public_text or term in read_text]
    return CheckResult(
        "secret-safe demo responses",
        not found,
        "no forbidden terms found" if not found else f"forbidden terms: {', '.join(found)}",
    )


def _auth_headers(username: str) -> dict[str, str]:
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": f"{username}-demo-password"},
    )
    if response.status_code != 200:
        return {}
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _format_statuses(statuses: dict[str, int]) -> str:
    return ", ".join(f"{path}={status}" for path, status in statuses.items())


if __name__ == "__main__":
    sys.exit(main())
