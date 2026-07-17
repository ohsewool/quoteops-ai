"""Safe operations, adapter, and guided-demo API contracts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.domain.customer_requests import ProductCode
from backend.domain.demo import DemoRunStatus


CSV_SCHEMA_VERSION = "competitor-reference-csv-v1"


class AuditEventResponse(BaseModel):
    id: int
    actor_user_id: int
    actor_username: str
    action: str
    entity_type: str
    entity_id: str
    request_id: str
    metadata: dict[str, object]
    created_at: datetime


class AuditEventPageResponse(BaseModel):
    items: list[AuditEventResponse]
    page: int
    page_size: int
    total: int


class OperationsDiagnosticsResponse(BaseModel):
    environment: str
    database_configured: bool
    docs_enabled: bool
    openapi_enabled: bool
    demo_enabled: bool
    cors_origin_count: int
    database_ready: bool
    alembic_revision: str | None
    audit_event_count: int


class CompetitorReferenceCsvImportRequest(BaseModel):
    schema_version: Literal[CSV_SCHEMA_VERSION]
    csv_text: str = Field(min_length=1, max_length=200_000)

    @field_validator("csv_text")
    @classmethod
    def reject_null_bytes(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("CSV input cannot contain NUL bytes")
        return value


class CompetitorReferenceCsvImportResponse(BaseModel):
    schema_version: str
    imported_count: int
    product_ids: list[int]
    competitor_ids: list[int]


class DemoGuideStepResponse(BaseModel):
    index: int
    total_steps: int
    key: str
    title: str
    description: str
    deep_link: str


class DemoRunResponse(BaseModel):
    id: int
    status: DemoRunStatus
    current_step: int
    version: int
    product_codes: list[ProductCode]
    artifacts: dict[str, list[int]]
    guide: DemoGuideStepResponse | None
    created_at: datetime
    updated_at: datetime


class DemoRunPageResponse(BaseModel):
    items: list[DemoRunResponse]


class DemoRunVersionedAction(BaseModel):
    version: int = Field(gt=0)
