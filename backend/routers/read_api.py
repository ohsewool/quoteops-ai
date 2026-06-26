import json

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.db import get_connection, rows_to_dicts, utc_now
from backend.routers.auth_api import require_owner_admin
from backend.schemas import (
    Competitor,
    CompetitorPrice,
    CostProfile,
    PriceTable,
    Product,
    ProductCategory,
    ProductCreate,
    ProductDetail,
    ProductOption,
    ProductOptionCreate,
    ProductOptionUpdate,
    ProductUpdate,
    QuantityLadder,
)
from backend.services.audit_logger import log_audit_event

router = APIRouter(prefix="/api", tags=["read-api"])


def _ensure_row_exists(connection, table: str, row_id: int, label: str) -> None:
    row = connection.execute(f"SELECT id FROM {table} WHERE id = ?", (row_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")


def _product_select_sql() -> str:
    return """
        SELECT
            p.id, p.category_id, pc.name AS category_name,
            p.quantity_ladder_id, ql.name AS quantity_ladder_name,
            p.name, p.slug, p.description, p.is_active,
            p.created_at, p.updated_at
        FROM products p
        LEFT JOIN product_categories pc ON pc.id = p.category_id
        LEFT JOIN quantity_ladders ql ON ql.id = p.quantity_ladder_id
    """


def _fetch_product(connection, product_id: int) -> dict:
    product = connection.execute(
        _product_select_sql() + " WHERE p.id = ?",
        (product_id,),
    ).fetchone()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return dict(product)


def _fetch_product_option(connection, option_id: int) -> dict:
    option = connection.execute(
        """
        SELECT
            id, product_id, option_type, option_name, option_value,
            sort_order, is_active, created_at, updated_at
        FROM product_options
        WHERE id = ?
        """,
        (option_id,),
    ).fetchone()
    if option is None:
        raise HTTPException(status_code=404, detail="Product option not found")
    return dict(option)


@router.get("/products", response_model=list[Product])
def list_products() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(_product_select_sql() + " ORDER BY p.id").fetchall()
        return rows_to_dicts(rows)


@router.post("/products", response_model=Product, status_code=201)
def create_product(request: ProductCreate, admin: dict = Depends(require_owner_admin)) -> dict:
    now = utc_now()
    with get_connection() as connection:
        if request.category_id is not None:
            _ensure_row_exists(connection, "product_categories", request.category_id, "Product category")
        if request.quantity_ladder_id is not None:
            _ensure_row_exists(connection, "quantity_ladders", request.quantity_ladder_id, "Quantity ladder")
        try:
            cursor = connection.execute(
                """
                INSERT INTO products (
                    category_id, quantity_ladder_id, name, slug, description,
                    is_active, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.category_id,
                    request.quantity_ladder_id,
                    request.name,
                    request.slug,
                    request.description,
                    int(request.is_active),
                    now,
                    now,
                ),
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Product slug must be unique.") from exc
        product = _fetch_product(connection, cursor.lastrowid)
        log_audit_event(
            connection,
            action="product_created",
            entity_type="product",
            entity_id=product["id"],
            entity_label=product["name"],
            after=product,
        )
        return product


@router.get("/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: int) -> dict:
    with get_connection() as connection:
        product_data = _fetch_product(connection, product_id)
        options = connection.execute(
            """
            SELECT
                id, product_id, option_type, option_name, option_value,
                sort_order, is_active, created_at, updated_at
            FROM product_options
            WHERE product_id = ?
            ORDER BY sort_order, id
            """,
            (product_id,),
        ).fetchall()
        product_data["options"] = rows_to_dicts(options)
        return product_data


@router.patch("/products/{product_id}", response_model=Product)
def update_product(product_id: int, request: ProductUpdate, admin: dict = Depends(require_owner_admin)) -> dict:
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No product fields to update.")

    allowed_fields = [
        "category_id",
        "quantity_ladder_id",
        "name",
        "slug",
        "description",
        "is_active",
    ]
    assignments = []
    values = []
    for field in allowed_fields:
        if field in updates:
            assignments.append(f"{field} = ?")
            value = updates[field]
            values.append(int(value) if field == "is_active" and value is not None else value)
    assignments.append("updated_at = ?")
    values.append(utc_now())
    values.append(product_id)

    with get_connection() as connection:
        _ensure_row_exists(connection, "products", product_id, "Product")
        before = _fetch_product(connection, product_id)
        if "category_id" in updates and updates["category_id"] is not None:
            _ensure_row_exists(connection, "product_categories", updates["category_id"], "Product category")
        if "quantity_ladder_id" in updates and updates["quantity_ladder_id"] is not None:
            _ensure_row_exists(connection, "quantity_ladders", updates["quantity_ladder_id"], "Quantity ladder")
        try:
            connection.execute(
                f"UPDATE products SET {', '.join(assignments)} WHERE id = ?",
                values,
            )
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Product slug must be unique.") from exc
        product = _fetch_product(connection, product_id)
        log_audit_event(
            connection,
            action="product_updated",
            entity_type="product",
            entity_id=product_id,
            entity_label=product["name"],
            before=before,
            after=product,
        )
        return product


@router.delete("/products/{product_id}", response_model=Product)
def deactivate_product(product_id: int, admin: dict = Depends(require_owner_admin)) -> dict:
    with get_connection() as connection:
        _ensure_row_exists(connection, "products", product_id, "Product")
        before = _fetch_product(connection, product_id)
        connection.execute(
            "UPDATE products SET is_active = 0, updated_at = ? WHERE id = ?",
            (utc_now(), product_id),
        )
        product = _fetch_product(connection, product_id)
        log_audit_event(
            connection,
            action="product_deleted",
            entity_type="product",
            entity_id=product_id,
            entity_label=product["name"],
            before=before,
            after=product,
        )
        return product


@router.get("/product-options", response_model=list[ProductOption])
def list_product_options(product_id: int | None = Query(default=None, ge=1)) -> list[dict]:
    filters = []
    values = []
    if product_id is not None:
        filters.append("product_id = ?")
        values.append(product_id)
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT
                id, product_id, option_type, option_name, option_value,
                sort_order, is_active, created_at, updated_at
            FROM product_options
            {where_clause}
            ORDER BY product_id, sort_order, id
            """,
            values,
        ).fetchall()
        return rows_to_dicts(rows)


@router.post("/product-options", response_model=ProductOption, status_code=201)
def create_product_option(request: ProductOptionCreate, admin: dict = Depends(require_owner_admin)) -> dict:
    now = utc_now()
    with get_connection() as connection:
        _ensure_row_exists(connection, "products", request.product_id, "Product")
        cursor = connection.execute(
            """
            INSERT INTO product_options (
                product_id, option_type, option_name, option_value, sort_order,
                is_active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.product_id,
                request.option_type,
                request.option_name,
                request.option_value,
                request.sort_order,
                int(request.is_active),
                now,
                now,
            ),
        )
        option = _fetch_product_option(connection, cursor.lastrowid)
        log_audit_event(
            connection,
            action="product_option_created",
            entity_type="product_option",
            entity_id=option["id"],
            entity_label=option["option_name"],
            after=option,
        )
        return option


@router.patch("/product-options/{option_id}", response_model=ProductOption)
def update_product_option(option_id: int, request: ProductOptionUpdate, admin: dict = Depends(require_owner_admin)) -> dict:
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No product option fields to update.")

    allowed_fields = [
        "product_id",
        "option_type",
        "option_name",
        "option_value",
        "sort_order",
        "is_active",
    ]
    assignments = []
    values = []
    for field in allowed_fields:
        if field in updates:
            assignments.append(f"{field} = ?")
            value = updates[field]
            values.append(int(value) if field == "is_active" and value is not None else value)
    assignments.append("updated_at = ?")
    values.append(utc_now())
    values.append(option_id)

    with get_connection() as connection:
        _ensure_row_exists(connection, "product_options", option_id, "Product option")
        before = _fetch_product_option(connection, option_id)
        if "product_id" in updates:
            _ensure_row_exists(connection, "products", updates["product_id"], "Product")
        connection.execute(
            f"UPDATE product_options SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        option = _fetch_product_option(connection, option_id)
        log_audit_event(
            connection,
            action="product_option_updated",
            entity_type="product_option",
            entity_id=option_id,
            entity_label=option["option_name"],
            before=before,
            after=option,
        )
        return option


@router.delete("/product-options/{option_id}", response_model=ProductOption)
def deactivate_product_option(option_id: int, admin: dict = Depends(require_owner_admin)) -> dict:
    with get_connection() as connection:
        _ensure_row_exists(connection, "product_options", option_id, "Product option")
        before = _fetch_product_option(connection, option_id)
        connection.execute(
            "UPDATE product_options SET is_active = 0, updated_at = ? WHERE id = ?",
            (utc_now(), option_id),
        )
        option = _fetch_product_option(connection, option_id)
        log_audit_event(
            connection,
            action="product_option_deleted",
            entity_type="product_option",
            entity_id=option_id,
            entity_label=option["option_name"],
            before=before,
            after=option,
        )
        return option


@router.get("/product-categories", response_model=list[ProductCategory])
def list_product_categories() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, name, slug, description, sort_order, is_active, created_at, updated_at
            FROM product_categories
            ORDER BY sort_order, id
            """
        ).fetchall()
        return rows_to_dicts(rows)


@router.get("/quantity-ladders", response_model=list[QuantityLadder])
def list_quantity_ladders() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, name, slug, quantities_json, description, created_at, updated_at
            FROM quantity_ladders
            ORDER BY id
            """
        ).fetchall()
        ladders = []
        for row in rows_to_dicts(rows):
            quantities_json = row.pop("quantities_json")
            row["quantities"] = json.loads(quantities_json or "[]")
            ladders.append(row)
        return ladders


@router.get("/competitors", response_model=list[Competitor])
def list_competitors() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, name, competitor_type, description, is_active, created_at, updated_at
            FROM competitors
            ORDER BY id
            """
        ).fetchall()
        return rows_to_dicts(rows)


@router.get("/competitor-prices", response_model=list[CompetitorPrice])
def list_competitor_prices(
    product_id: int | None = Query(default=None, ge=1),
    quantity: int | None = Query(default=None, ge=1),
    option_summary: str | None = Query(default=None),
) -> list[dict]:
    filters = []
    values = []
    if product_id is not None:
        filters.append("product_id = ?")
        values.append(product_id)
    if quantity is not None:
        filters.append("quantity = ?")
        values.append(quantity)
    if option_summary:
        filters.append("LOWER(TRIM(option_summary)) = ?")
        values.append(" ".join(option_summary.strip().lower().split()))

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    with get_connection() as connection:
        rows = connection.execute(
            f"""
            SELECT
                id, competitor_id, product_id, quantity, option_summary, price,
                source_note, collected_at, created_at, updated_at
            FROM competitor_prices
            {where_clause}
            ORDER BY product_id, quantity, competitor_id
            """,
            values,
        ).fetchall()
        return rows_to_dicts(rows)


@router.get("/cost-profiles", response_model=list[CostProfile])
def list_cost_profiles() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                id, product_id, quantity, option_summary, unit_cost, fixed_cost,
                minimum_margin_rate, minimum_price, created_at, updated_at
            FROM cost_profiles
            ORDER BY product_id, quantity
            """
        ).fetchall()
        return rows_to_dicts(rows)


@router.get("/price-tables", response_model=list[PriceTable])
def list_price_tables() -> list[dict]:
    with get_connection() as connection:
        table_rows = connection.execute(
            """
            SELECT id, product_id, name, status, strategy_name, created_at, updated_at
            FROM price_tables
            ORDER BY id
            """
        ).fetchall()
        tables = rows_to_dicts(table_rows)

        item_rows = connection.execute(
            """
            SELECT
                id, price_table_id, quantity, option_summary, final_price,
                margin_rate, created_at, updated_at
            FROM price_table_items
            ORDER BY price_table_id, quantity
            """
        ).fetchall()
        items_by_table: dict[int, list[dict]] = {}
        for item in rows_to_dicts(item_rows):
            items_by_table.setdefault(item["price_table_id"], []).append(item)

        for table in tables:
            table["items"] = items_by_table.get(table["id"], [])

        return tables
