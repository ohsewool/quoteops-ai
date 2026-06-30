from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen


BACKEND_URL_ENV = "QUOTEOPS_DEPLOYED_BACKEND_URL"
FRONTEND_URL_ENV = "QUOTEOPS_DEPLOYED_FRONTEND_URL"
BACKEND_GET_PATHS = [
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/system/status",
    "/openapi.json",
    "/api/dashboard/insights",
    "/api/demo/status",
    "/api/demo/guide",
]
PUBLIC_BACKEND_PATHS = {
    "/api/health",
    "/api/health/live",
    "/api/health/ready",
    "/api/system/status",
    "/openapi.json",
}
AUTH_OPTIONAL_PATHS = {
    "/api/dashboard/insights",
    "/api/demo/status",
    "/api/demo/guide",
}
SECRET_PATTERNS = [
    "database_url",
    "quoteops_auth_secret",
    "openai_api_key",
    ("begin " + "private key"),
    "postgresql://real-user:real-password@",
]
APP_SHELL_MARKERS = ["quoteops", "<html", "vite", "root"]
TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class CheckResult:
    status: str
    name: str
    detail: str


def main() -> int:
    backend_url = normalize_url(os.getenv(BACKEND_URL_ENV))
    frontend_url = normalize_url(os.getenv(FRONTEND_URL_ENV))
    results: list[CheckResult] = []

    if backend_url:
        results.extend(run_backend_checks(backend_url))
    else:
        results.append(CheckResult("SKIP", "deployed backend", f"{BACKEND_URL_ENV} is not set"))

    if frontend_url:
        results.extend(run_frontend_checks(frontend_url))
    else:
        results.append(CheckResult("SKIP", "deployed frontend", f"{FRONTEND_URL_ENV} is not set"))

    if backend_url and frontend_url:
        results.append(check_cors(backend_url, frontend_url))
    else:
        results.append(CheckResult("SKIP", "deployed CORS", "backend and frontend URLs are both required"))

    for result in results:
        print(f"{result.status}: {result.name} - {result.detail}")

    return 1 if any(result.status == "FAIL" for result in results) else 0


def normalize_url(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().rstrip("/")
    if not cleaned:
        return None
    return cleaned


def run_backend_checks(base_url: str) -> list[CheckResult]:
    results: list[CheckResult] = []
    responses: dict[str, tuple[int | None, str, dict[str, str]]] = {}
    for path in BACKEND_GET_PATHS:
        status, body, headers = fetch_text(urljoin(base_url + "/", path.lstrip("/")))
        responses[path] = (status, body, headers)
        if path in PUBLIC_BACKEND_PATHS:
            passed = status == 200
            results.append(
                CheckResult(
                    "PASS" if passed else "FAIL",
                    f"backend {path}",
                    f"status {status}" if status is not None else body,
                )
            )
        elif path in AUTH_OPTIONAL_PATHS and status in {200, 401, 403}:
            results.append(
                CheckResult(
                    "PASS",
                    f"backend {path}",
                    f"status {status}; auth-protected is acceptable",
                )
            )
        else:
            results.append(CheckResult("FAIL", f"backend {path}", f"status {status}"))

    results.append(check_system_status_secret_safety(responses["/api/system/status"][1]))
    results.append(check_openapi_json(responses["/openapi.json"][0], responses["/openapi.json"][1]))
    return results


def run_frontend_checks(base_url: str) -> list[CheckResult]:
    status, body, _headers = fetch_text(base_url)
    if status != 200:
        return [CheckResult("FAIL", "frontend root", f"status {status}" if status else body)]
    lowered = body.lower()
    appears_to_be_shell = any(marker in lowered for marker in APP_SHELL_MARKERS)
    return [
        CheckResult(
            "PASS" if appears_to_be_shell else "FAIL",
            "frontend root",
            "status 200 and app shell marker found"
            if appears_to_be_shell
            else "status 200 but app shell marker not found",
        )
    ]


def check_cors(backend_url: str, frontend_url: str) -> CheckResult:
    status, _body, headers = fetch_text(
        urljoin(backend_url + "/", "api/health"),
        headers={"Origin": frontend_url},
    )
    allow_origin = headers.get("access-control-allow-origin", "")
    if status != 200:
        return CheckResult("FAIL", "deployed CORS", f"health status {status}")
    if allow_origin in {frontend_url, "*"}:
        return CheckResult(
            "PASS",
            "deployed CORS",
            f"access-control-allow-origin={allow_origin}; frontend origin appears allowed",
        )
    return CheckResult(
        "WARN",
        "deployed CORS",
        f"access-control-allow-origin={allow_origin or '(missing)'}; verify Render CORS settings",
    )


def check_system_status_secret_safety(body: str) -> CheckResult:
    lowered = body.lower()
    found = [pattern for pattern in SECRET_PATTERNS if pattern in lowered]
    if found:
        return CheckResult("FAIL", "system status secret safety", f"forbidden markers: {', '.join(found)}")
    return CheckResult("PASS", "system status secret safety", "no obvious secret markers found")


def check_openapi_json(status: int | None, body: str) -> CheckResult:
    if status != 200:
        return CheckResult("FAIL", "OpenAPI JSON", f"status {status}")
    try:
        parsed = json.loads(body)
    except json.JSONDecodeError:
        return CheckResult("FAIL", "OpenAPI JSON", "response is not valid JSON")
    path_count = len(parsed.get("paths", {}))
    if path_count <= 0:
        return CheckResult("FAIL", "OpenAPI JSON", "no paths found")
    return CheckResult("PASS", "OpenAPI JSON", f"path_count={path_count}")


def fetch_text(url: str, *, headers: dict[str, str] | None = None) -> tuple[int | None, str, dict[str, str]]:
    request = Request(url, headers=headers or {}, method="GET")
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = response.read()
            return (
                response.status,
                data.decode("utf-8", errors="replace"),
                {key.lower(): value for key, value in response.headers.items()},
            )
    except HTTPError as exc:
        data = exc.read()
        return (
            exc.code,
            data.decode("utf-8", errors="replace"),
            {key.lower(): value for key, value in exc.headers.items()},
        )
    except URLError as exc:
        return None, f"request failed: {exc.reason}", {}
    except TimeoutError:
        return None, "request timed out", {}


if __name__ == "__main__":
    sys.exit(main())
