from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth import get_optional_current_user
from backend.db import get_db
from backend.models import User
from backend.schemas import QuoteExplanationRequest, QuoteExplanationResponse
from backend.services.audit_service import create_audit_log
from backend.services.explanation_service import explain_quote


router = APIRouter(prefix="/api/explanations", tags=["explanations"])


@router.post("/quote", response_model=QuoteExplanationResponse)
def explain_quote_result(
    payload: QuoteExplanationRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> QuoteExplanationResponse:
    response = explain_quote(db, payload)
    create_audit_log(
        db,
        action="quote_explanation_created",
        entity_type="explanation",
        summary=f"Quote explanation created for product {response.product_id}.",
        metadata={
            "product_id": response.product_id,
            "quantity": response.quantity,
            "proposed_unit_price": response.proposed_unit_price,
            "validation_status": response.validation_status,
            "risk_level": response.risk_level,
            "explanation_source": response.explanation_source,
        },
        actor=current_user,
    )
    return response
