from datetime import datetime, timezone

from fastapi import APIRouter, Request, Response

from backend.config import get_safe_config_summary, get_settings
from backend.db import database_connection_ok
from backend.schemas import (
    HealthLiveResponse,
    HealthReadyResponse,
    HealthResponse,
    SystemStatusResponse,
)


router = APIRouter(tags=["system"])


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service="quoteops-ai",
        environment=getattr(settings, "environment", "local"),
        timestamp=_utc_now(),
    )


@router.get("/api/health/live", response_model=HealthLiveResponse)
def health_live() -> HealthLiveResponse:
    return HealthLiveResponse(
        status="alive",
        service="quoteops-ai",
        timestamp=_utc_now(),
    )


@router.get("/api/health/ready", response_model=HealthReadyResponse)
def health_ready(response: Response) -> HealthReadyResponse:
    settings = get_settings()
    database_ok = database_connection_ok()
    config_ok = _safe_config_ok()
    ready = database_ok and config_ok
    if not ready:
        response.status_code = 503
    return HealthReadyResponse(
        status="ready" if ready else "not_ready",
        service="quoteops-ai",
        database_connection_ok=database_ok,
        database_type=settings.database_type,
        config_ok=config_ok,
        timestamp=_utc_now(),
    )


@router.get("/api/system/status", response_model=SystemStatusResponse)
def system_status(request: Request) -> SystemStatusResponse:
    settings = get_settings()
    database_ok = database_connection_ok()
    openapi_available = _openapi_available(request)
    status = "ok" if database_ok and openapi_available else "degraded"
    return SystemStatusResponse(
        service="quoteops-ai",
        status=status,
        environment=getattr(settings, "environment", "local"),
        database={
            "configured": bool(settings.database_url),
            "type": settings.database_type,
            "connection_ok": database_ok,
        },
        cors={
            "configured": getattr(settings, "cors_origins_configured", True),
            "origin_count": getattr(settings, "cors_origin_count", 0),
            "wildcard_enabled": getattr(settings, "cors_wildcard_enabled", False),
        },
        features={
            "demo_tools_enabled": settings.demo_tools_enabled,
            "openapi_available": openapi_available,
            "openai_configured": settings.openai_configured,
        },
        security={
            "secrets_exposed": False,
            "raw_db_url_exposed": False,
        },
        timestamp=_utc_now(),
    )


def _safe_config_ok() -> bool:
    try:
        get_safe_config_summary()
        return True
    except Exception:
        return False


def _openapi_available(request: Request) -> bool:
    try:
        request.app.openapi()
        return True
    except Exception:
        return False
