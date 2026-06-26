from fastapi import APIRouter, Query

from backend.db import get_connection
from backend.schemas.audit import AuditLogListResponse
from backend.services.audit_logger import list_audit_logs

router = APIRouter(prefix="/api", tags=["audit-logs"])


@router.get("/audit-logs", response_model=AuditLogListResponse)
def read_audit_logs(
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: int | None = Query(default=None, ge=1),
    actor_name: str | None = Query(default=None),
    created_from: str | None = Query(default=None),
    created_to: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> dict:
    with get_connection() as connection:
        return list_audit_logs(
            connection,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_name=actor_name,
            created_from=created_from,
            created_to=created_to,
            limit=limit,
            offset=offset,
        )
