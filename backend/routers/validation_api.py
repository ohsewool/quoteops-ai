from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth import get_optional_current_user
from backend.db import get_db
from backend.models import User
from backend.schemas import PriceValidationRequest, PriceValidationResponse
from backend.services.validation_service import validate_price
from backend.services.audit_service import create_audit_log


router = APIRouter(prefix="/api/price-validation", tags=["price validation"])


@router.post("", response_model=PriceValidationResponse)
def validate_candidate_price(
    payload: PriceValidationRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> PriceValidationResponse:
    response = validate_price(db, payload)
    create_audit_log(
        db,
        action="price_validation_created",
        entity_type="price_validation",
        summary=f"Price validation created with status {response.validation_status}.",
        metadata={
            "product_id": response.product_id,
            "quantity": response.quantity,
            "candidate_unit_price": response.candidate_unit_price,
            "validation_status": response.validation_status,
            "risk_level": response.risk_level,
        },
        actor=current_user,
    )
    return response
