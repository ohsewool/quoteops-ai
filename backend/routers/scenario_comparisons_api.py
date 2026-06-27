from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.auth import require_role
from backend.db import get_db
from backend.models import User
from backend.schemas import ScenarioComparisonCreate, ScenarioComparisonResponse
from backend.services.audit_service import create_audit_log
from backend.services.scenario_comparison_service import (
    create_scenario_comparison,
    get_scenario_comparison,
    list_scenario_comparisons,
)


router = APIRouter(prefix="/api/scenario-comparisons", tags=["scenario comparisons"])


@router.post("", response_model=ScenarioComparisonResponse, status_code=status.HTTP_201_CREATED)
def create_comparison(
    payload: ScenarioComparisonCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> ScenarioComparisonResponse:
    response = create_scenario_comparison(db, payload, current_user.username)
    create_audit_log(
        db,
        action="scenario_comparison_created",
        entity_type="scenario_comparison",
        entity_id=response.id,
        summary=f"Scenario comparison {response.id} created.",
        metadata={
            "comparison_id": response.id,
            "product_id": response.product_id,
            "scenario_count": response.scenario_count,
            "highest_margin_label": response.summary.highest_margin_label,
        },
        actor=current_user,
    )
    return response


@router.get("", response_model=list[ScenarioComparisonResponse])
def list_comparisons(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> list[ScenarioComparisonResponse]:
    response = list_scenario_comparisons(db)
    create_audit_log(
        db,
        action="scenario_comparison_list_viewed",
        entity_type="scenario_comparison",
        summary="Scenario comparison list viewed.",
        metadata={"result_count": len(response)},
        actor=current_user,
    )
    return response


@router.get("/{comparison_id}", response_model=ScenarioComparisonResponse)
def get_comparison(
    comparison_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> ScenarioComparisonResponse:
    response = get_scenario_comparison(db, comparison_id)
    create_audit_log(
        db,
        action="scenario_comparison_viewed",
        entity_type="scenario_comparison",
        entity_id=response.id,
        summary=f"Scenario comparison {response.id} viewed.",
        metadata={"comparison_id": response.id, "scenario_count": response.scenario_count},
        actor=current_user,
    )
    return response
