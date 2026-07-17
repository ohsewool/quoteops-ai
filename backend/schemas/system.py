from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str = "quoteops-ai-v2"


class ReadinessResponse(BaseModel):
    status: str
    service: str = "quoteops-ai-v2"


class SystemStatusResponse(BaseModel):
    environment: str
    database_configured: bool
    docs_enabled: bool
    openapi_enabled: bool
    demo_enabled: bool
    cors_origin_count: int
