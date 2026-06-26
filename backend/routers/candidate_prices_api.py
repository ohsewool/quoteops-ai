from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.schemas import CandidatePriceRequest, CandidatePriceResponse
from backend.services.candidate_price_service import generate_candidate_prices


router = APIRouter(prefix="/api/candidate-prices", tags=["candidate prices"])


@router.post("", response_model=CandidatePriceResponse)
def create_candidate_prices(
    payload: CandidatePriceRequest, db: Session = Depends(get_db)
) -> CandidatePriceResponse:
    return generate_candidate_prices(db, payload)
