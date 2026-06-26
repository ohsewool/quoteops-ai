from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.schemas import PriceValidationRequest, PriceValidationResponse
from backend.services.validation_service import validate_price


router = APIRouter(prefix="/api/price-validation", tags=["price validation"])


@router.post("", response_model=PriceValidationResponse)
def validate_candidate_price(
    payload: PriceValidationRequest, db: Session = Depends(get_db)
) -> PriceValidationResponse:
    return validate_price(db, payload)
