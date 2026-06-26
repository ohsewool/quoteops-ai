from __future__ import annotations

import json
import sqlite3
from typing import Any

from backend.db import utc_now


def log_agent_step(
    connection: sqlite3.Connection,
    *,
    step_type: str,
    title: str,
    message: str,
    status: str = "completed",
    metadata: dict[str, Any] | None = None,
    pricing_session_id: int | None = None,
    candidate_table_id: int | None = None,
    validation_result_id: int | None = None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO agent_logs (
            pricing_session_id, candidate_table_id, validation_result_id,
            step_type, title, message, status, metadata_json, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            pricing_session_id,
            candidate_table_id,
            validation_result_id,
            step_type,
            title,
            message,
            status,
            json.dumps(metadata or {}),
            utc_now(),
        ),
    )
    return cursor.lastrowid


def list_agent_logs(
    connection: sqlite3.Connection,
    *,
    pricing_session_id: int | None = None,
    candidate_table_id: int | None = None,
    validation_result_id: int | None = None,
) -> list[dict[str, Any]]:
    where = []
    values: list[Any] = []
    if pricing_session_id is not None:
        where.append("pricing_session_id = ?")
        values.append(pricing_session_id)
    if candidate_table_id is not None:
        where.append("candidate_table_id = ?")
        values.append(candidate_table_id)
    if validation_result_id is not None:
        where.append("validation_result_id = ?")
        values.append(validation_result_id)

    query = """
        SELECT
            id, pricing_session_id, candidate_table_id, validation_result_id,
            step_type, title, message, status, metadata_json, created_at
        FROM agent_logs
    """
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY id ASC"

    rows = connection.execute(query, values).fetchall()
    return [
        {
            "id": row["id"],
            "pricing_session_id": row["pricing_session_id"],
            "candidate_table_id": row["candidate_table_id"],
            "validation_result_id": row["validation_result_id"],
            "step_type": row["step_type"],
            "title": row["title"],
            "message": row["message"],
            "status": row["status"],
            "metadata": json.loads(row["metadata_json"] or "{}"),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
