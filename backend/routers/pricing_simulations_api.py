from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.auth import require_role
from backend.db import get_db
from backend.models import User
from backend.schemas import PricingSimulationCreate, PricingSimulationResponse
from backend.services.audit_service import create_audit_log
from backend.services.pricing_simulation_service import (
    create_pricing_simulation,
    get_pricing_simulation,
    list_pricing_simulations,
)


router = APIRouter(prefix="/api/pricing-simulations", tags=["pricing simulations"])


@router.post(
    "",
    response_model=PricingSimulationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_simulation(
    payload: PricingSimulationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> PricingSimulationResponse:
    response = create_pricing_simulation(db, payload, current_user.username)
    create_audit_log(
        db,
        action="pricing_simulation_created",
        entity_type="pricing_simulation",
        entity_id=response.id,
        summary=f"Pricing simulation {response.id} created.",
        metadata={
            "simulation_id": response.id,
            "product_id": response.product_id,
            "scenario_count": response.scenario_count,
            "include_competitor_context": response.include_competitor_context,
        },
        actor=current_user,
    )
    return response


@router.get("", response_model=list[PricingSimulationResponse])
def list_simulations(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> list[PricingSimulationResponse]:
    response = list_pricing_simulations(db)
    create_audit_log(
        db,
        action="pricing_simulation_viewed",
        entity_type="pricing_simulation",
        summary="Pricing simulations list viewed.",
        metadata={"result_count": len(response)},
        actor=current_user,
    )
    return response


@router.get("/{simulation_id}", response_model=PricingSimulationResponse)
def get_simulation(
    simulation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> PricingSimulationResponse:
    response = get_pricing_simulation(db, simulation_id)
    create_audit_log(
        db,
        action="pricing_simulation_viewed",
        entity_type="pricing_simulation",
        entity_id=response.id,
        summary=f"Pricing simulation {response.id} viewed.",
        metadata={"simulation_id": response.id, "scenario_count": response.scenario_count},
        actor=current_user,
    )
    return response
