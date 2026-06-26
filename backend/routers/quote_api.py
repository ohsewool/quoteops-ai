from fastapi import APIRouter, HTTPException

from backend.db import get_connection
from backend.schemas.quote import QuotePreviewRequest, QuotePreviewResponse
from backend.services.quote_calculator import QuoteCalculationError, calculate_quote

router = APIRouter(prefix="/api/quotes", tags=["quotes"])


@router.post("/preview", response_model=QuotePreviewResponse)
def preview_quote(request: QuotePreviewRequest) -> dict:
    try:
        with get_connection() as connection:
            return calculate_quote(
                connection,
                product_id=request.product_id,
                product_slug=request.product_slug,
                quantity=request.quantity,
                option_summary=request.option_summary,
            )
    except QuoteCalculationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
