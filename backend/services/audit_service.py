import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import AuditLog, User


SENSITIVE_METADATA_KEYS = {
    "password",
    "password_hash",
    "access_token",
    "token",
    "auth_secret",
    "database_url",
    "openai_api_key",
}


def create_audit_log(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: int | str | None = None,
    summary: str,
    metadata: dict[str, Any] | None = None,
    actor: User | None = None,
) -> AuditLog:
    safe_metadata = _sanitize_metadata(metadata or {})
    audit_log = AuditLog(
        actor_user_id=actor.id if actor else None,
        actor_username=actor.username if actor else "anonymous",
        actor_role=actor.role if actor else "anonymous",
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        summary=summary,
        metadata_json=json.dumps(safe_metadata, sort_keys=True, separators=(",", ":")),
    )
    db.add(audit_log)
    db.commit()
    db.refresh(audit_log)
    return audit_log


def list_audit_logs(
    db: Session,
    *,
    action: str | None = None,
    entity_type: str | None = None,
    actor_username: str | None = None,
    limit: int = 50,
) -> list[AuditLog]:
    safe_limit = min(max(limit, 1), 100)
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    if actor_username:
        query = query.filter(AuditLog.actor_username == actor_username)
    return query.order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(safe_limit).all()


def get_audit_log(db: Session, audit_log_id: int) -> AuditLog:
    audit_log = db.get(AuditLog, audit_log_id)
    if audit_log is None:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return audit_log


def _sanitize_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized_key = key.lower()
        if normalized_key in SENSITIVE_METADATA_KEYS or "password" in normalized_key:
            continue
        if isinstance(value, dict):
            safe[key] = _sanitize_metadata(value)
        elif isinstance(value, list):
            safe[key] = [_sanitize_value(item) for item in value]
        else:
            safe[key] = value
    return safe


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _sanitize_metadata(value)
    return value
