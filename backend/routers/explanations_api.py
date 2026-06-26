from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.schemas import QuoteExplanationRequest, QuoteExplanationResponse
from backend.services.explanation_service import explain_quote


router = APIRouter(prefix="/api/explanations", tags=["explanations"])


@router.post("/quote", response_model=QuoteExplanationResponse)
def explain_quote_result(
    payload: QuoteExplanationRequest, db: Session = Depends(get_db)
) -> QuoteExplanationResponse:
    return explain_quote(db, payload)
