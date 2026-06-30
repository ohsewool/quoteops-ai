from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "frontend" / "src" / "App.jsx"
MAIN = ROOT / "frontend" / "src" / "main.jsx"
CLIENT = ROOT / "frontend" / "src" / "api" / "client.js"
FRONTEND_SOURCE = ROOT / "frontend" / "src"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_app_imports_react_when_runtime_could_need_react_symbol():
    text = _read(APP)

    assert 'from "react"' in text
    assert "import React" in text


def test_main_has_valid_react_mount_imports():
    text = _read(MAIN)

    assert 'import React from "react"' in text
    assert 'from "react-dom/client"' in text
    assert 'import App from "./App.jsx"' in text
    assert "createRoot" in text
    assert "React.StrictMode" in text


def test_api_client_keeps_configured_base_url_and_local_fallback():
    text = _read(CLIENT)

    assert "VITE_API_BASE_URL" in text
    assert "http://127.0.0.1:8000" in text


def test_frontend_source_does_not_expose_backend_secrets():
    combined = "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND_SOURCE.rglob("*") if path.is_file())

    assert "DATABASE_URL" not in combined
    assert "QUOTEOPS_AUTH_SECRET" not in combined
