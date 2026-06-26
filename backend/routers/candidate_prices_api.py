from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth import get_optional_current_user
from backend.db import get_db
from backend.models import User
from backend.schemas import CandidatePriceRequest, CandidatePriceResponse
from backend.services.candidate_price_service import generate_candidate_prices
from backend.services.audit_service import create_audit_log


router = APIRouter(prefix="/api/candidate-prices", tags=["candidate prices"])


@router.post("", response_model=CandidatePriceResponse)
def create_candidate_prices(
    payload: CandidatePriceRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
) -> CandidatePriceResponse:
    response = generate_candidate_prices(db, payload)
    create_audit_log(
        db,
        action="candidate_prices_generated",
        entity_type="candidate_prices",
        summary=f"Candidate prices generated for product {response.product_id}.",
        metadata={
            "product_id": response.product_id,
            "quantity": response.quantity,
            "candidate_count": len(response.candidates),
            "unit_cost": response.unit_cost,
        },
        actor=current_user,
    )
    return response
