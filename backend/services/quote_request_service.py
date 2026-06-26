from __future__ import annotations

import sqlite3
from typing import Any

from backend.db import rows_to_dicts, utc_now
from backend.schemas.quote_request import QUOTE_REQUEST_STATUSES, QuoteRequestCreate, QuoteRequestUpdate
from backend.services.quote_calculator import calculate_quote


class QuoteRequestError(Exception):
    status_code = 400

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(detail)


class QuoteRequestNotFoundError(QuoteRequestError):
    status_code = 404


def _fetch_product(connection: sqlite3.Connection, product_id: int) -> sqlite3.Row:
    product = connection.execute(
        """
        SELECT id, name
        FROM products
        WHERE id = ? AND is_active = 1
        """,
        (product_id,),
    ).fetchone()
    if product is None:
        raise QuoteRequestNotFoundError("Active product not found.")
    return product


def _fetch_quote_request(connection: sqlite3.Connection, request_id: int) -> dict[str, Any]:
    quote_request = connection.execute(
        """
        SELECT
            id, product_id, product_name_snapshot, requester_name, requester_email,
            requester_phone, company_name, quantity, option_summary, request_note,
            status, quoted_price, quoted_unit_price, quote_source, admin_note,
            created_at, updated_at
        FROM quote_requests
        WHERE id = ?
        """,
        (request_id,),
    ).fetchone()
    if quote_request is None:
        raise QuoteRequestNotFoundError("Quote request not found.")
    return dict(quote_request)


def create_quote_request(
    connection: sqlite3.Connection,
    request: QuoteRequestCreate,
) -> dict[str, Any]:
    product = _fetch_product(connection, request.product_id)
    now = utc_now()
    cursor = connection.execute(
        """
        INSERT INTO quote_requests (
            product_id, product_name_snapshot, requester_name, requester_email,
            requester_phone, company_name, quantity, option_summary, request_note,
            status, quoted_price, quoted_unit_price, quote_source, admin_note,
            created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'submitted', NULL, NULL, NULL, NULL, ?, ?)
        """,
        (
            product["id"],
            product["name"],
            request.requester_name,
            request.requester_email,
            request.requester_phone,
            request.company_name,
            request.quantity,
            request.option_summary,
            request.request_note,
            now,
            now,
        ),
    )
    return _fetch_quote_request(connection, cursor.lastrowid)


def list_quote_requests(
    connection: sqlite3.Connection,
    status: str | None = None,
) -> list[dict[str, Any]]:
    filters = []
    values: list[Any] = []
    if status:
        if status not in QUOTE_REQUEST_STATUSES:
            raise QuoteRequestError("Unsupported quote request status.")
        filters.append("status = ?")
        values.append(status)
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    rows = connection.execute(
        f"""
        SELECT
            id, product_id, product_name_snapshot, requester_name, requester_email,
            requester_phone, company_name, quantity, option_summary, request_note,
            status, quoted_price, quoted_unit_price, quote_source, admin_note,
            created_at, updated_at
        FROM quote_requests
        {where_clause}
        ORDER BY id DESC
        """,
        values,
    ).fetchall()
    return rows_to_dicts(rows)


def get_quote_request(connection: sqlite3.Connection, request_id: int) -> dict[str, Any]:
    return _fetch_quote_request(connection, request_id)


def update_quote_request(
    connection: sqlite3.Connection,
    request_id: int,
    request: QuoteRequestUpdate,
) -> dict[str, Any]:
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise QuoteRequestError("No quote request fields to update.")

    assignments = []
    values: list[Any] = []
    for field in ["status", "admin_note"]:
        if field in updates:
            assignments.append(f"{field} = ?")
            values.append(updates[field])
    assignments.append("updated_at = ?")
    values.append(utc_now())
    values.append(request_id)

    _fetch_quote_request(connection, request_id)
    connection.execute(
        f"UPDATE quote_requests SET {', '.join(assignments)} WHERE id = ?",
        values,
    )
    return _fetch_quote_request(connection, request_id)


def preview_quote_for_request(
    connection: sqlite3.Connection,
    request_id: int,
) -> dict[str, Any]:
    quote_request = _fetch_quote_request(connection, request_id)
    quote_preview = calculate_quote(
        connection,
        product_id=quote_request["product_id"],
        quantity=quote_request["quantity"],
        option_summary=quote_request["option_summary"],
    )
    now = utc_now()
    connection.execute(
        """
        UPDATE quote_requests
        SET
            status = 'quoted',
            quoted_price = ?,
            quoted_unit_price = ?,
            quote_source = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            quote_preview["quote_price"],
            quote_preview["unit_price"],
            quote_preview["calculation_source"],
            now,
            request_id,
        ),
    )
    return {
        "quote_request": _fetch_quote_request(connection, request_id),
        "quote_preview": quote_preview,
    }
