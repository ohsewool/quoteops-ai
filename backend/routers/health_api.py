from datetime import datetime, timezone

from fastapi import APIRouter

from backend.config import get_settings
from backend.schemas import HealthResponse, SystemStatusResponse


router = APIRouter(tags=["system"])


@router.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="quoteops-ai",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/api/system/status", response_model=SystemStatusResponse)
def system_status() -> SystemStatusResponse:
    settings = get_settings()
    return SystemStatusResponse(
        service="quoteops-ai",
        database_configured=bool(settings.database_url),
        database_type=settings.database_type,
        openai_configured=settings.openai_configured,
        demo_tools_enabled=settings.demo_tools_enabled,
    )
