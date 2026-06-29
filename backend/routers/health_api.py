from datetime import datetime, timezone

from fastapi import APIRouter

from backend.config import get_settings
from backend.db import database_connection_ok
from backend.schemas import HealthResponse, SystemStatusResponse


router = APIRouter(tags=["system"])


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service="quoteops-ai",
        timestamp=datetime.now(timezone.utc).isoformat(),
        database_type=settings.database_type,
        database_connection_ok=database_connection_ok(),
    )


@router.get("/api/system/status", response_model=SystemStatusResponse)
def system_status() -> SystemStatusResponse:
    settings = get_settings()
    return SystemStatusResponse(
        service="quoteops-ai",
        database_configured=bool(settings.database_url),
        database_type=settings.database_type,
        database_url_safe=settings.database_url_safe,
        database_connection_ok=database_connection_ok(),
        environment=getattr(settings, "environment", "local"),
        openai_configured=settings.openai_configured,
        demo_tools_enabled=settings.demo_tools_enabled,
    )
