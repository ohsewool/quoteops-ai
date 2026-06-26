from fastapi import APIRouter, Depends, HTTPException, Response

from backend.db import get_connection, rows_to_dicts, utc_now
from backend.routers.auth_api import require_manager_or_owner_admin
from backend.schemas import (
    CostProfile,
    CostProfileCreate,
    CostProfileUpdate,
    PriceTable,
    PriceTableCreate,
    PriceTableItem,
    PriceTableItemCreate,
    PriceTableItemUpdate,
    PriceTableUpdate,
)
from backend.services.audit_logger import log_audit_event

router = APIRouter(prefix="/api", tags=["internal-pricing"])

PRICE_TABLE_STATUSES = {"draft", "active", "archived"}


def _ensure_row_exists(connection, table: str, row_id: int, label: str) -> None:
    row = connection.execute(f"SELECT id FROM {table} WHERE id = ?", (row_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")


def _validate_status(status: str) -> None:
    if status not in PRICE_TABLE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Price table status must be one of: draft, active, archived.",
        )


def _archive_other_active_tables(connection, product_id: int, price_table_id: int | None = None) -> None:
    now = utc_now()
    if price_table_id is None:
        connection.execute(
            """
            UPDATE price_tables
            SET status = 'archived', updated_at = ?
            WHERE product_id = ? AND status = 'active'
            """,
            (now, product_id),
        )
    else:
        connection.execute(
            """
            UPDATE price_tables
            SET status = 'archived', updated_at = ?
            WHERE product_id = ? AND status = 'active' AND id != ?
            """,
            (now, product_id, price_table_id),
        )


def _fetch_cost_profile(connection, cost_profile_id: int):
    return connection.execute(
        """
        SELECT
            id, product_id, quantity, option_summary, unit_cost, fixed_cost,
            minimum_margin_rate, minimum_price, created_at, updated_at
        FROM cost_profiles
        WHERE id = ?
        """,
        (cost_profile_id,),
    ).fetchone()


def _fetch_price_table(connection, price_table_id: int) -> dict:
    table = connection.execute(
        """
        SELECT id, product_id, name, status, strategy_name, created_at, updated_at
        FROM price_tables
        WHERE id = ?
        """,
        (price_table_id,),
    ).fetchone()
    if table is None:
        raise HTTPException(status_code=404, detail="Price table not found")

    items = connection.execute(
        """
        SELECT
            id, price_table_id, quantity, option_summary, final_price,
            margin_rate, created_at, updated_at
        FROM price_table_items
        WHERE price_table_id = ?
        ORDER BY quantity, id
        """,
        (price_table_id,),
    ).fetchall()
    table_data = dict(table)
    table_data["items"] = rows_to_dicts(items)
    return table_data


def _fetch_price_table_item(connection, item_id: int):
    return connection.execute(
        """
        SELECT
            id, price_table_id, quantity, option_summary, final_price,
            margin_rate, created_at, updated_at
        FROM price_table_items
        WHERE id = ?
        """,
        (item_id,),
    ).fetchone()


@router.post("/cost-profiles", response_model=CostProfile, status_code=201)
def create_cost_profile(
    request: CostProfileCreate,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    now = utc_now()
    with get_connection() as connection:
        _ensure_row_exists(connection, "products", request.product_id, "Product")
        cursor = connection.execute(
            """
            INSERT INTO cost_profiles (
                product_id, quantity, option_summary, unit_cost, fixed_cost,
                minimum_margin_rate, minimum_price, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.product_id,
                request.quantity,
                request.option_summary,
                request.unit_cost,
                request.fixed_cost,
                request.minimum_margin_rate,
                request.minimum_price,
                now,
                now,
            ),
        )
        cost_profile = dict(_fetch_cost_profile(connection, cursor.lastrowid))
        log_audit_event(
            connection,
            action="cost_profile_created",
            entity_type="cost_profile",
            entity_id=cost_profile["id"],
            entity_label=cost_profile["option_summary"],
            after=cost_profile,
        )
        return cost_profile


@router.patch("/cost-profiles/{cost_profile_id}", response_model=CostProfile)
def update_cost_profile(
    cost_profile_id: int,
    request: CostProfileUpdate,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No cost profile fields to update.")

    allowed_fields = [
        "product_id",
        "quantity",
        "option_summary",
        "unit_cost",
        "fixed_cost",
        "minimum_margin_rate",
        "minimum_price",
    ]
    assignments = []
    values = []
    for field in allowed_fields:
        if field in updates:
            assignments.append(f"{field} = ?")
            values.append(updates[field])

    assignments.append("updated_at = ?")
    values.append(utc_now())
    values.append(cost_profile_id)

    with get_connection() as connection:
        _ensure_row_exists(connection, "cost_profiles", cost_profile_id, "Cost profile")
        before = _fetch_cost_profile(connection, cost_profile_id)
        if "product_id" in updates:
            _ensure_row_exists(connection, "products", updates["product_id"], "Product")
        connection.execute(
            f"UPDATE cost_profiles SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        cost_profile = dict(_fetch_cost_profile(connection, cost_profile_id))
        log_audit_event(
            connection,
            action="cost_profile_updated",
            entity_type="cost_profile",
            entity_id=cost_profile_id,
            entity_label=cost_profile["option_summary"],
            before=dict(before),
            after=cost_profile,
        )
        return cost_profile


@router.delete("/cost-profiles/{cost_profile_id}", status_code=204)
def delete_cost_profile(
    cost_profile_id: int,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> Response:
    with get_connection() as connection:
        _ensure_row_exists(connection, "cost_profiles", cost_profile_id, "Cost profile")
        before = _fetch_cost_profile(connection, cost_profile_id)
        connection.execute("DELETE FROM cost_profiles WHERE id = ?", (cost_profile_id,))
        log_audit_event(
            connection,
            action="cost_profile_deleted",
            entity_type="cost_profile",
            entity_id=cost_profile_id,
            entity_label=before["option_summary"],
            before=dict(before),
        )
    return Response(status_code=204)


@router.get("/price-tables/{price_table_id}", response_model=PriceTable)
def get_price_table(price_table_id: int) -> dict:
    with get_connection() as connection:
        return _fetch_price_table(connection, price_table_id)


@router.post("/price-tables", response_model=PriceTable, status_code=201)
def create_price_table(
    request: PriceTableCreate,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    _validate_status(request.status)
    now = utc_now()
    with get_connection() as connection:
        _ensure_row_exists(connection, "products", request.product_id, "Product")
        previous_active = []
        if request.status == "active":
            previous_active = [
                dict(row)
                for row in connection.execute(
                    "SELECT id, name, status FROM price_tables WHERE product_id = ? AND status = 'active'",
                    (request.product_id,),
                ).fetchall()
            ]
            _archive_other_active_tables(connection, request.product_id)
            for table in previous_active:
                log_audit_event(
                    connection,
                    action="price_table_archived",
                    entity_type="price_table",
                    entity_id=table["id"],
                    entity_label=table["name"],
                    before=table,
                    after={**table, "status": "archived"},
                    metadata={"reason": "new_active_price_table_created"},
                )
        cursor = connection.execute(
            """
            INSERT INTO price_tables (product_id, name, status, strategy_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request.product_id,
                request.name,
                request.status,
                request.strategy_name,
                now,
                now,
            ),
        )
        table = _fetch_price_table(connection, cursor.lastrowid)
        log_audit_event(
            connection,
            action="price_table_created",
            entity_type="price_table",
            entity_id=table["id"],
            entity_label=table["name"],
            after=table,
            metadata={"archived_previous_active_count": len(previous_active)},
        )
        return table


@router.patch("/price-tables/{price_table_id}", response_model=PriceTable)
def update_price_table(
    price_table_id: int,
    request: PriceTableUpdate,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No price table fields to update.")
    if "status" in updates:
        _validate_status(updates["status"])

    allowed_fields = ["product_id", "name", "status", "strategy_name"]
    assignments = []
    values = []
    for field in allowed_fields:
        if field in updates:
            assignments.append(f"{field} = ?")
            values.append(updates[field])

    assignments.append("updated_at = ?")
    values.append(utc_now())
    values.append(price_table_id)

    with get_connection() as connection:
        existing = connection.execute(
            "SELECT id, product_id FROM price_tables WHERE id = ?",
            (price_table_id,),
        ).fetchone()
        if existing is None:
            raise HTTPException(status_code=404, detail="Price table not found")
        before = _fetch_price_table(connection, price_table_id)
        product_id = updates.get("product_id", existing["product_id"])
        if "product_id" in updates:
            _ensure_row_exists(connection, "products", updates["product_id"], "Product")
        if updates.get("status") == "active":
            previous_active = [
                dict(row)
                for row in connection.execute(
                    "SELECT id, name, status FROM price_tables WHERE product_id = ? AND status = 'active' AND id != ?",
                    (product_id, price_table_id),
                ).fetchall()
            ]
            _archive_other_active_tables(connection, product_id, price_table_id)
            for table in previous_active:
                log_audit_event(
                    connection,
                    action="price_table_archived",
                    entity_type="price_table",
                    entity_id=table["id"],
                    entity_label=table["name"],
                    before=table,
                    after={**table, "status": "archived"},
                    metadata={"reason": "price_table_status_set_active"},
                )
        connection.execute(
            f"UPDATE price_tables SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        table = _fetch_price_table(connection, price_table_id)
        log_audit_event(
            connection,
            action="price_table_updated",
            entity_type="price_table",
            entity_id=price_table_id,
            entity_label=table["name"],
            before=before,
            after=table,
        )
        return table


@router.delete("/price-tables/{price_table_id}", response_model=PriceTable)
def archive_price_table(
    price_table_id: int,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    with get_connection() as connection:
        _ensure_row_exists(connection, "price_tables", price_table_id, "Price table")
        before = _fetch_price_table(connection, price_table_id)
        connection.execute(
            "UPDATE price_tables SET status = 'archived', updated_at = ? WHERE id = ?",
            (utc_now(), price_table_id),
        )
        table = _fetch_price_table(connection, price_table_id)
        log_audit_event(
            connection,
            action="price_table_archived",
            entity_type="price_table",
            entity_id=price_table_id,
            entity_label=table["name"],
            before=before,
            after=table,
        )
        return table


@router.get("/price-tables/{price_table_id}/items", response_model=list[PriceTableItem])
def list_price_table_items(price_table_id: int) -> list[dict]:
    with get_connection() as connection:
        _ensure_row_exists(connection, "price_tables", price_table_id, "Price table")
        rows = connection.execute(
            """
            SELECT
                id, price_table_id, quantity, option_summary, final_price,
                margin_rate, created_at, updated_at
            FROM price_table_items
            WHERE price_table_id = ?
            ORDER BY quantity, id
            """,
            (price_table_id,),
        ).fetchall()
        return rows_to_dicts(rows)


@router.post("/price-tables/{price_table_id}/items", response_model=PriceTableItem, status_code=201)
def create_price_table_item(
    price_table_id: int,
    request: PriceTableItemCreate,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    now = utc_now()
    with get_connection() as connection:
        _ensure_row_exists(connection, "price_tables", price_table_id, "Price table")
        cursor = connection.execute(
            """
            INSERT INTO price_table_items (
                price_table_id, quantity, option_summary, final_price,
                margin_rate, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                price_table_id,
                request.quantity,
                request.option_summary,
                request.final_price,
                request.margin_rate,
                now,
                now,
            ),
        )
        item = dict(_fetch_price_table_item(connection, cursor.lastrowid))
        log_audit_event(
            connection,
            action="price_table_item_created",
            entity_type="price_table_item",
            entity_id=item["id"],
            entity_label=item["option_summary"],
            after=item,
        )
        return item


@router.patch("/price-table-items/{item_id}", response_model=PriceTableItem)
def update_price_table_item(
    item_id: int,
    request: PriceTableItemUpdate,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No price table item fields to update.")

    allowed_fields = ["quantity", "option_summary", "final_price", "margin_rate"]
    assignments = []
    values = []
    for field in allowed_fields:
        if field in updates:
            assignments.append(f"{field} = ?")
            values.append(updates[field])

    assignments.append("updated_at = ?")
    values.append(utc_now())
    values.append(item_id)

    with get_connection() as connection:
        _ensure_row_exists(connection, "price_table_items", item_id, "Price table item")
        before = _fetch_price_table_item(connection, item_id)
        connection.execute(
            f"UPDATE price_table_items SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        item = dict(_fetch_price_table_item(connection, item_id))
        log_audit_event(
            connection,
            action="price_table_item_updated",
            entity_type="price_table_item",
            entity_id=item_id,
            entity_label=item["option_summary"],
            before=dict(before),
            after=item,
        )
        return item


@router.delete("/price-table-items/{item_id}", status_code=204)
def delete_price_table_item(
    item_id: int,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> Response:
    with get_connection() as connection:
        _ensure_row_exists(connection, "price_table_items", item_id, "Price table item")
        before = _fetch_price_table_item(connection, item_id)
        connection.execute("DELETE FROM price_table_items WHERE id = ?", (item_id,))
        log_audit_event(
            connection,
            action="price_table_item_deleted",
            entity_type="price_table_item",
            entity_id=item_id,
            entity_label=before["option_summary"],
            before=dict(before),
        )
    return Response(status_code=204)
