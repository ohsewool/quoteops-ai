from fastapi import APIRouter, HTTPException, Query

from backend.db import get_connection
from backend.schemas.price_comparison import (
    PriceTableComparisonResponse,
    PriceTableHistoryEntry,
)
from backend.services.price_table_comparison import (
    PriceTableComparisonError,
    compare_price_tables,
    list_price_table_history,
)

router = APIRouter(prefix="/api", tags=["price-table-comparison"])


@router.get(
    "/price-tables/{price_table_id}/compare",
    response_model=PriceTableComparisonResponse,
)
def compare_price_table(
    price_table_id: int,
    baseline_price_table_id: int | None = Query(default=None, ge=1),
) -> dict:
    try:
        with get_connection() as connection:
            return compare_price_tables(
                connection,
                comparison_price_table_id=price_table_id,
                baseline_price_table_id=baseline_price_table_id,
            )
    except PriceTableComparisonError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get("/price-tables/history", response_model=list[PriceTableHistoryEntry])
def read_price_table_history(product_id: int | None = Query(default=None, ge=1)) -> list[dict]:
    with get_connection() as connection:
        return list_price_table_history(connection, product_id=product_id)


@router.get(
    "/products/{product_id}/price-table-history",
    response_model=list[PriceTableHistoryEntry],
)
def read_product_price_table_history(product_id: int) -> list[dict]:
    with get_connection() as connection:
        return list_price_table_history(connection, product_id=product_id)

