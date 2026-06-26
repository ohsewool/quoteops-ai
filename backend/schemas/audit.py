from typing import Any

from pydantic import BaseModel


class AuditLog(BaseModel):
    id: int
    actor_id: int | None
    actor_name: str | None
    actor_role: str | None
    action: str
    entity_type: str
    entity_id: int | None
    entity_label: str | None
    before: Any | None
    after: Any | None
    metadata: dict[str, Any]
    ip_address: str | None
    user_agent: str | None
    created_at: str


class AuditLogListResponse(BaseModel):
    items: list[AuditLog]
    total: int
    limit: int
    offset: int
