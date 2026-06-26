from fastapi import APIRouter, HTTPException

from backend.db import get_connection
from backend.schemas.scenario_comparison import (
    ScenarioComparisonRequest,
    ScenarioComparisonResponse,
)
from backend.services.scenario_comparison import (
    ScenarioComparisonError,
    compare_pricing_scenarios,
)

router = APIRouter(prefix="/api/pricing-scenarios", tags=["pricing-scenarios"])


@router.post("/compare", response_model=ScenarioComparisonResponse)
def compare_scenarios(request: ScenarioComparisonRequest) -> dict:
    try:
        with get_connection() as connection:
            return compare_pricing_scenarios(
                connection,
                base_type=request.base.scenario_type,
                base_id=request.base.scenario_id,
                compare_type=request.compare.scenario_type,
                compare_id=request.compare.scenario_id,
            )
    except ScenarioComparisonError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
