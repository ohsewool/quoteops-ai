from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from backend.models.audit_event import AuditEvent

SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "authorization",
    "database_url",
    "password",
    "private_key",
    "secret",
    "token",
)
REDACTED = "[REDACTED]"


def sanitize_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): REDACTED
            if any(fragment in str(key).lower() for fragment in SENSITIVE_KEY_FRAGMENTS)
            else sanitize_metadata(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_metadata(item) for item in value]
    if isinstance(value, tuple):
        return [sanitize_metadata(item) for item in value]
    return value


def append_audit_event(
    session: Session,
    *,
    actor_user_id: int,
    action: str,
    entity_type: str,
    entity_id: str,
    request_id: str,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        request_id=request_id,
        metadata_json=sanitize_metadata(metadata or {}),
    )
    session.add(event)
    return event
