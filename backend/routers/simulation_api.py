from fastapi import APIRouter, HTTPException

from backend.db import get_connection
from backend.schemas import PricingSimulationRequest, PricingSimulationResponse
from backend.services.pricing_simulator import PricingSimulationError, simulate_pricing

router = APIRouter(prefix="/api/simulations", tags=["pricing-simulations"])


@router.post("/pricing", response_model=PricingSimulationResponse)
def simulate_pricing_table(request: PricingSimulationRequest) -> dict:
    try:
        with get_connection() as connection:
            return simulate_pricing(
                connection,
                product_id=request.product_id,
                product_slug=request.product_slug,
                candidate_table_id=request.candidate_table_id,
                baseline_price_table_id=request.baseline_price_table_id,
                option_summary=request.option_summary,
                volume_assumptions=[
                    item.model_dump() for item in request.volume_assumptions
                ] if request.volume_assumptions else None,
            )
    except PricingSimulationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
