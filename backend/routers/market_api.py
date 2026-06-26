from fastapi import APIRouter, Depends, HTTPException, Query, Response

from backend.db import get_connection, utc_now
from backend.routers.auth_api import require_manager_or_owner_admin
from backend.schemas import (
    Competitor,
    CompetitorCreate,
    CompetitorPrice,
    CompetitorPriceCreate,
    CompetitorPriceUpdate,
    CompetitorUpdate,
    MarketReferenceResponse,
)
from backend.services.market_reference import MarketReferenceError, build_market_reference
from backend.services.audit_logger import log_audit_event

router = APIRouter(prefix="/api", tags=["market-reference"])


def _ensure_row_exists(connection, table: str, row_id: int, label: str) -> None:
    row = connection.execute(f"SELECT id FROM {table} WHERE id = ?", (row_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")


def _fetch_competitor_price(connection, price_id: int):
    return connection.execute(
        """
        SELECT
            id, competitor_id, product_id, quantity, option_summary, price,
            source_note, collected_at, created_at, updated_at
        FROM competitor_prices
        WHERE id = ?
        """,
        (price_id,),
    ).fetchone()


@router.post("/competitors", response_model=Competitor, status_code=201)
def create_competitor(request: CompetitorCreate, admin: dict = Depends(require_manager_or_owner_admin)) -> dict:
    now = utc_now()
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO competitors (name, competitor_type, description, is_active, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request.name,
                request.competitor_type,
                request.description,
                int(request.is_active),
                now,
                now,
            ),
        )
        row = connection.execute(
            """
            SELECT id, name, competitor_type, description, is_active, created_at, updated_at
            FROM competitors
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
        competitor = dict(row)
        log_audit_event(
            connection,
            action="competitor_created",
            entity_type="competitor",
            entity_id=competitor["id"],
            entity_label=competitor["name"],
            after=competitor,
        )
        return competitor


@router.patch("/competitors/{competitor_id}", response_model=Competitor)
def update_competitor(
    competitor_id: int,
    request: CompetitorUpdate,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No competitor fields to update.")

    allowed_fields = ["name", "competitor_type", "description", "is_active"]
    assignments = []
    values = []
    for field in allowed_fields:
        if field in updates:
            assignments.append(f"{field} = ?")
            values.append(int(updates[field]) if field == "is_active" else updates[field])

    assignments.append("updated_at = ?")
    values.append(utc_now())
    values.append(competitor_id)

    with get_connection() as connection:
        _ensure_row_exists(connection, "competitors", competitor_id, "Competitor")
        before = connection.execute(
            """
            SELECT id, name, competitor_type, description, is_active, created_at, updated_at
            FROM competitors
            WHERE id = ?
            """,
            (competitor_id,),
        ).fetchone()
        connection.execute(
            f"UPDATE competitors SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        row = connection.execute(
            """
            SELECT id, name, competitor_type, description, is_active, created_at, updated_at
            FROM competitors
            WHERE id = ?
            """,
            (competitor_id,),
        ).fetchone()
        competitor = dict(row)
        log_audit_event(
            connection,
            action="competitor_updated",
            entity_type="competitor",
            entity_id=competitor_id,
            entity_label=competitor["name"],
            before=dict(before),
            after=competitor,
        )
        return competitor


@router.post("/competitor-prices", response_model=CompetitorPrice, status_code=201)
def create_competitor_price(
    request: CompetitorPriceCreate,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    now = utc_now()
    collected_at = request.collected_at or now
    with get_connection() as connection:
        _ensure_row_exists(connection, "competitors", request.competitor_id, "Competitor")
        _ensure_row_exists(connection, "products", request.product_id, "Product")
        cursor = connection.execute(
            """
            INSERT INTO competitor_prices (
                competitor_id, product_id, quantity, option_summary, price,
                source_note, collected_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                request.competitor_id,
                request.product_id,
                request.quantity,
                request.option_summary,
                request.price,
                request.source_note,
                collected_at,
                now,
                now,
            ),
        )
        row = _fetch_competitor_price(connection, cursor.lastrowid)
        price = dict(row)
        log_audit_event(
            connection,
            action="competitor_price_created",
            entity_type="competitor_price",
            entity_id=price["id"],
            entity_label=price["option_summary"],
            after=price,
        )
        return price


@router.patch("/competitor-prices/{price_id}", response_model=CompetitorPrice)
def update_competitor_price(
    price_id: int,
    request: CompetitorPriceUpdate,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> dict:
    updates = request.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No competitor price fields to update.")

    allowed_fields = [
        "competitor_id",
        "product_id",
        "quantity",
        "option_summary",
        "price",
        "source_note",
        "collected_at",
    ]
    assignments = []
    values = []
    for field in allowed_fields:
        if field in updates:
            assignments.append(f"{field} = ?")
            values.append(updates[field])

    assignments.append("updated_at = ?")
    values.append(utc_now())
    values.append(price_id)

    with get_connection() as connection:
        _ensure_row_exists(connection, "competitor_prices", price_id, "Competitor price")
        before = _fetch_competitor_price(connection, price_id)
        if "competitor_id" in updates:
            _ensure_row_exists(connection, "competitors", updates["competitor_id"], "Competitor")
        if "product_id" in updates:
            _ensure_row_exists(connection, "products", updates["product_id"], "Product")
        connection.execute(
            f"UPDATE competitor_prices SET {', '.join(assignments)} WHERE id = ?",
            values,
        )
        row = _fetch_competitor_price(connection, price_id)
        price = dict(row)
        log_audit_event(
            connection,
            action="competitor_price_updated",
            entity_type="competitor_price",
            entity_id=price_id,
            entity_label=price["option_summary"],
            before=dict(before),
            after=price,
        )
        return price


@router.delete("/competitor-prices/{price_id}", status_code=204)
def delete_competitor_price(
    price_id: int,
    admin: dict = Depends(require_manager_or_owner_admin),
) -> Response:
    with get_connection() as connection:
        _ensure_row_exists(connection, "competitor_prices", price_id, "Competitor price")
        before = _fetch_competitor_price(connection, price_id)
        connection.execute("DELETE FROM competitor_prices WHERE id = ?", (price_id,))
        log_audit_event(
            connection,
            action="competitor_price_deleted",
            entity_type="competitor_price",
            entity_id=price_id,
            entity_label=before["option_summary"],
            before=dict(before),
        )
    return Response(status_code=204)


@router.get("/market-reference", response_model=MarketReferenceResponse)
def get_market_reference(
    quantity: int = Query(ge=1),
    option_summary: str = Query(min_length=1),
    product_id: int | None = Query(default=None, ge=1),
    product_slug: str | None = Query(default=None),
) -> dict:
    try:
        with get_connection() as connection:
            return build_market_reference(
                connection,
                product_id=product_id,
                product_slug=product_slug,
                quantity=quantity,
                option_summary=option_summary,
            )
    except MarketReferenceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
