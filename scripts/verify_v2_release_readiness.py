"""Run safe local V2 release-readiness smoke checks without revealing secrets.

This command reads the ignored local V2 environment only to establish
connections. It never prints connection strings, passwords, tokens, or keys.
It does not migrate, truncate, or otherwise modify either database.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from alembic.config import Config
from alembic.script import ScriptDirectory
from dotenv import dotenv_values
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from backend.main import create_app


EXPECTED_TABLES = {
    "alembic_version",
    "users",
    "audit_events",
    "customer_requests",
    "quotes",
    "quote_lines",
    "quote_revisions",
    "quote_revision_lines",
    "products",
    "cost_profiles",
    "competitors",
    "competitor_references",
    "pricing_checks",
    "price_candidates",
    "price_candidate_lines",
    "price_validation_results",
    "price_validation_checks",
    "approval_requests",
    "approval_decisions",
    "html_reports",
    "copilot_outputs",
    "demo_runs",
}

REQUIRED_OPENAPI_PATHS = {
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/customer-requests",
    "/api/quotes",
    "/api/approval-requests",
    "/api/html-reports",
    "/api/operations/diagnostics",
    "/api/demo/runs",
}

HEALTH_SECRET_MARKERS = (
    "quoteops_auth_secret",
    "auth_secret",
    "openai_api_key",
    "database_url",
    "password",
    "begin private key",
)


def _git(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *arguments], text=True, capture_output=True, check=False)


def _database_name(url: str) -> str:
    return url.rsplit("/", 1)[-1]


def _tracked_risky_files() -> list[str]:
    tracked = _git("ls-files")
    if tracked.returncode:
        raise RuntimeError("Unable to inspect tracked V2 files")
    return [
        path
        for path in tracked.stdout.splitlines()
        if path == ".env"
        or path.startswith("frontend/dist/")
        or path.startswith("frontend/node_modules/")
        or path.endswith((".sqlite", ".sqlite3", ".pyc"))
        or "/__pycache__/" in path
    ]


def _revision_and_tables(url: str) -> tuple[str | None, set[str]]:
    engine = create_engine(url, future=True)
    try:
        with engine.connect() as connection:
            revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
            tables = set(
                connection.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                ).scalars()
            )
        return str(revision) if revision else None, tables
    finally:
        engine.dispose()


def main() -> int:
    values = dotenv_values(".env")
    application_url = values.get("QUOTEOPS_DATABASE_URL")
    test_url = values.get("QUOTEOPS_TEST_DATABASE_URL")
    if not application_url or not test_url:
        print("release_readiness=BLOCKED configuration_incomplete")
        return 1
    application_name = _database_name(application_url)
    test_name = _database_name(test_url)
    if application_name != "quoteops_ai_v2" or test_name != "quoteops_ai_v2_test" or application_name == test_name:
        print("release_readiness=BLOCKED database_separation_invalid")
        return 1

    head = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini"))).get_current_head()
    application_revision, application_tables = _revision_and_tables(application_url)
    test_revision, test_tables = _revision_and_tables(test_url)
    with TestClient(create_app()) as client:
        responses = {path: client.get(path) for path in ("/api/health", "/api/health/live", "/api/health/ready", "/openapi.json")}
    health_text = "\n".join(
        responses[path].text.lower() for path in ("/api/health", "/api/health/live", "/api/health/ready")
    )
    openapi_paths = set(responses["/openapi.json"].json().get("paths", {})) if responses["/openapi.json"].status_code == 200 else set()
    env_ignored = _git("check-ignore", "-q", ".env").returncode == 0
    env_tracked = _git("ls-files", "--error-unmatch", ".env").returncode == 0
    risky_files = _tracked_risky_files()

    checks = {
        "application_database_name_confirmed": application_name == "quoteops_ai_v2",
        "test_database_name_confirmed": test_name == "quoteops_ai_v2_test",
        "database_names_distinct": application_name != test_name,
        "application_at_alembic_head": application_revision == head,
        "test_at_alembic_head": test_revision == head,
        "application_schema_matches_expected": application_tables == EXPECTED_TABLES,
        "test_schema_matches_expected": test_tables == EXPECTED_TABLES,
        "health_live_ready_openapi_200": all(response.status_code == 200 for response in responses.values()),
        "required_openapi_paths_present": REQUIRED_OPENAPI_PATHS.issubset(openapi_paths),
        "health_secret_markers_absent": all(marker not in health_text for marker in HEALTH_SECRET_MARKERS),
        "openapi_connection_string_absent": "postgresql+psycopg://" not in responses["/openapi.json"].text.lower(),
        "v2_env_ignored": env_ignored,
        "v2_env_untracked": not env_tracked,
        "risky_tracked_files_absent": not risky_files,
    }
    for name, passed in checks.items():
        print(f"{name}={passed}")
    if risky_files:
        print(f"risky_tracked_file_count={len(risky_files)}")
    if not all(checks.values()):
        print("release_readiness=BLOCKED")
        return 1
    print("release_readiness=VERIFIED_LOCAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
