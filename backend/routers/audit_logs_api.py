from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.auth import require_role
from backend.db import get_db
from backend.models import User
from backend.schemas import AuditLogResponse
from backend.services.audit_service import get_audit_log, list_audit_logs


router = APIRouter(prefix="/api/audit-logs", tags=["audit logs"])


@router.get("", response_model=list[AuditLogResponse])
def list_logs(
    action: str | None = None,
    entity_type: str | None = None,
    actor_username: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("manager")),
) -> list[AuditLogResponse]:
    return list_audit_logs(
        db,
        action=action,
        entity_type=entity_type,
        actor_username=actor_username,
        limit=limit,
    )


@router.get("/{audit_log_id}", response_model=AuditLogResponse)
def get_log(
    audit_log_id: int,
    db: Session = Depends(get_db),
    _current_user: User = Depends(require_role("manager")),
) -> AuditLogResponse:
    return get_audit_log(db, audit_log_id)
