import os
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import app


client = TestClient(app)

CURRENT_MINIMUM_PATHS = {
    "/",
    "/api/health",
}

PR01_REQUIRED_PATHS = {
    "/api/health",
    "/api/system/status",
    "/api/products",
    "/api/products/{product_id}",
    "/api/competitors",
    "/api/competitors/{competitor_id}",
    "/api/competitor-prices",
    "/api/cost-profiles",
    "/api/cost-profiles/{cost_profile_id}",
    "/api/price-tables",
    "/api/price-tables/{price_table_id}",
    "/api/price-tables/{price_table_id}/items",
}


def _current_branch_name() -> str:
    for env_name in ("GITHUB_HEAD_REF", "GITHUB_REF_NAME"):
        branch_name = os.getenv(env_name)
        if branch_name:
            return branch_name

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return ""

    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def test_openapi_contains_current_minimum_routes():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = set(response.json()["paths"])
    assert CURRENT_MINIMUM_PATHS <= paths


def test_pr01_branch_requires_backend_foundation_routes():
    branch_name = _current_branch_name()
    if "real-pr-01-backend-foundation" not in branch_name:
        return

    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = set(response.json()["paths"])
    missing_paths = sorted(PR01_REQUIRED_PATHS - paths)
    assert not missing_paths, f"Missing PR-01 API paths: {missing_paths}"
