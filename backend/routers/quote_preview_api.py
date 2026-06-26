from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth import get_optional_current_user
from backend.db import get_db
from backend.models import User
from backend.schemas import QuotePreviewRequest, QuotePreviewResponse
from backend.services.quote_preview_service import calculate_quote_preview
from backend.services.audit_service import create_audit_log


router = APIRouter(prefix="/api/quote-preview", tags=["quote preview"])


@router.post("", response_model=QuotePreviewResponse)
def preview_quote(
    payload: QuotePreviewRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> QuotePreviewResponse:
    response = calculate_quote_preview(db, payload)
    create_audit_log(
        db,
        action="quote_preview_created",
        entity_type="quote_preview",
        summary=f"Quote preview created for product {response.product_id}.",
        metadata={
            "product_id": response.product_id,
            "quantity": response.quantity,
            "suggested_unit_price": response.suggested_unit_price,
            "suggested_total_price": response.suggested_total_price,
        },
        actor=current_user,
    )
    return response
