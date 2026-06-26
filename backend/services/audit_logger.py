from __future__ import annotations

import json
import sqlite3
from typing import Any

from backend.db import utc_now


def _json_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _loads(value: str | None) -> Any:
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


def audit_actor(admin: dict[str, Any] | None = None) -> dict[str, Any]:
    if not admin:
        return {"actor_id": None, "actor_name": None, "actor_role": None}
    return {
        "actor_id": admin.get("id"),
        "actor_name": admin.get("display_name") or admin.get("email"),
        "actor_role": admin.get("role"),
    }


def log_audit_event(
    connection: sqlite3.Connection,
    *,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    entity_label: str | None = None,
    actor_id: int | None = None,
    actor_name: str | None = None,
    actor_role: str | None = None,
    before: Any = None,
    after: Any = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO audit_logs (
            actor_id, actor_name, actor_role, action, entity_type, entity_id,
            entity_label, before_json, after_json, metadata_json,
            ip_address, user_agent, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            actor_id,
            actor_name,
            actor_role,
            action,
            entity_type,
            entity_id,
            entity_label,
            _json_or_none(before),
            _json_or_none(after),
            _json_or_none(metadata or {}),
            ip_address,
            user_agent,
            utc_now(),
        ),
    )
    return cursor.lastrowid


def list_audit_logs(
    connection: sqlite3.Connection,
    *,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    actor_name: str | None = None,
    created_from: str | None = None,
    created_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    where = []
    values: list[Any] = []
    if action:
        where.append("action = ?")
        values.append(action)
    if entity_type:
        where.append("entity_type = ?")
        values.append(entity_type)
    if entity_id is not None:
        where.append("entity_id = ?")
        values.append(entity_id)
    if actor_name:
        where.append("LOWER(actor_name) LIKE ?")
        values.append(f"%{actor_name.strip().lower()}%")
    if created_from:
        where.append("created_at >= ?")
        values.append(created_from)
    if created_to:
        where.append("created_at <= ?")
        values.append(created_to)

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = connection.execute(
        f"SELECT COUNT(*) FROM audit_logs {where_clause}",
        values,
    ).fetchone()[0]
    rows = connection.execute(
        f"""
        SELECT
            id, actor_id, actor_name, actor_role, action, entity_type,
            entity_id, entity_label, before_json, after_json, metadata_json,
            ip_address, user_agent, created_at
        FROM audit_logs
        {where_clause}
        ORDER BY id DESC
        LIMIT ? OFFSET ?
        """,
        [*values, limit, offset],
    ).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["before"] = _loads(item.pop("before_json"))
        item["after"] = _loads(item.pop("after_json"))
        item["metadata"] = _loads(item.pop("metadata_json")) or {}
        items.append(item)
    return {"items": items, "total": total, "limit": limit, "offset": offset}
