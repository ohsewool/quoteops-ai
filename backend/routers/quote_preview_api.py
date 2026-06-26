from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.schemas import QuotePreviewRequest, QuotePreviewResponse
from backend.services.quote_preview_service import calculate_quote_preview


router = APIRouter(prefix="/api/quote-preview", tags=["quote preview"])


@router.post("", response_model=QuotePreviewResponse)
def preview_quote(
    payload: QuotePreviewRequest, db: Session = Depends(get_db)
) -> QuotePreviewResponse:
    return calculate_quote_preview(db, payload)
