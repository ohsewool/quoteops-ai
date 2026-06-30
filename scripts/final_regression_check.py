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

PUBLIC_STATUS_PATHS = [
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/system/status",
    "/openapi.json",
]
AUTH_REQUIRED_PATHS = [
    "/api/dashboard/summary",
    "/api/dashboard/insights",
    "/api/demo/status",
    "/api/demo/guide",
]
REQUIRED_OPENAPI_PATHS = [
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/system/status",
    "/api/quote-preview",
    "/api/candidate-prices",
    "/api/price-validation",
    "/api/approval-requests",
    "/api/explanations/quote",
    "/api/audit-logs",
    "/api/import/products",
    "/api/export/products.csv",
    "/api/pricing-simulations",
    "/api/customer-quote-requests",
    "/api/price-tables",
    "/api/price-table-snapshots/compare",
    "/api/workflow-jobs",
    "/api/strategy-templates",
    "/api/dashboard/summary",
    "/api/dashboard/metrics",
    "/api/dashboard/insights",
    "/api/dashboard/insights/rules",
    "/api/scenario-comparisons",
    "/api/html-reports",
    "/api/demo/status",
    "/api/demo/seed",
    "/api/demo/scenario/full",
    "/api/demo/guide",
]
FORBIDDEN_RESPONSE_TERMS = [
    "database_url",
    "quoteops_auth_secret",
    "auth_secret",
    "openai_api_key",
    "sk-test",
    "super-secret-password",
    "super-secret-auth-value",
    ("begin " + "private key"),
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
        _check_public_status_paths(),
        _check_authenticated_read_paths(),
        _check_openapi_paths(),
        _check_secret_safe_status_responses(),
    ]
    for result in results:
        prefix = "PASS" if result.passed else "FAIL"
        print(f"{prefix}: {result.name} - {result.detail}")
    return 0 if all(result.passed for result in results) else 1


def _check_public_status_paths() -> CheckResult:
    statuses = {path: client.get(path).status_code for path in PUBLIC_STATUS_PATHS}
    passed = all(status == 200 for status in statuses.values())
    return CheckResult("public health/status/openapi", passed, _format_statuses(statuses))


def _check_authenticated_read_paths() -> CheckResult:
    headers = _auth_headers("viewer")
    statuses = {path: client.get(path, headers=headers).status_code for path in AUTH_REQUIRED_PATHS}
    passed = all(status == 200 for status in statuses.values())
    return CheckResult("authenticated read surface", passed, _format_statuses(statuses))


def _check_openapi_paths() -> CheckResult:
    response = client.get("/openapi.json")
    if response.status_code != 200:
        return CheckResult("openapi required paths", False, f"openapi status {response.status_code}")
    paths = response.json().get("paths", {})
    missing = [path for path in REQUIRED_OPENAPI_PATHS if path not in paths]
    return CheckResult(
        "openapi required paths",
        not missing,
        "all required paths present" if not missing else f"missing: {', '.join(missing)}",
    )


def _check_secret_safe_status_responses() -> CheckResult:
    combined = "".join(client.get(path).text.lower() for path in PUBLIC_STATUS_PATHS[:-1])
    found = [term for term in FORBIDDEN_RESPONSE_TERMS if term in combined]
    return CheckResult(
        "secret-safe status responses",
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
