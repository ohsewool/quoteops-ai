from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.auth import require_role
from backend.db import get_db
from backend.models import User
from backend.schemas import (
    CandidatePriceResponse,
    PricingSimulationResponse,
    StrategyTemplateCandidatePriceRequest,
    StrategyTemplateCreate,
    StrategyTemplatePricingSimulationRequest,
    StrategyTemplateResponse,
    StrategyTemplateUpdate,
)
from backend.services.audit_service import create_audit_log
from backend.services.strategy_template_service import (
    apply_strategy_template_to_candidate_prices,
    apply_strategy_template_to_pricing_simulation,
    create_strategy_template,
    disable_strategy_template,
    get_strategy_template,
    list_strategy_templates,
    update_strategy_template,
)


router = APIRouter(prefix="/api/strategy-templates", tags=["strategy templates"])


@router.post(
    "",
    response_model=StrategyTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_template(
    payload: StrategyTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> StrategyTemplateResponse:
    response = create_strategy_template(db, payload, current_user.username)
    create_audit_log(
        db,
        action="strategy_template_created",
        entity_type="strategy_template",
        entity_id=response.id,
        summary=f"Strategy template {response.strategy_code} created.",
        metadata={
            "template_id": response.id,
            "strategy_code": response.strategy_code,
            "risk_preference": response.risk_preference,
            "margin_rate_count": len(response.margin_rates),
        },
        actor=current_user,
    )
    return response


@router.get("", response_model=list[StrategyTemplateResponse])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> list[StrategyTemplateResponse]:
    return list_strategy_templates(db)


@router.get("/{template_id}", response_model=StrategyTemplateResponse)
def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> StrategyTemplateResponse:
    return get_strategy_template(db, template_id)


@router.put("/{template_id}", response_model=StrategyTemplateResponse)
def update_template(
    template_id: int,
    payload: StrategyTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> StrategyTemplateResponse:
    response = update_strategy_template(db, template_id, payload)
    create_audit_log(
        db,
        action="strategy_template_updated",
        entity_type="strategy_template",
        entity_id=response.id,
        summary=f"Strategy template {response.strategy_code} updated.",
        metadata={
            "template_id": response.id,
            "strategy_code": response.strategy_code,
            "active": response.active,
        },
        actor=current_user,
    )
    return response


@router.delete("/{template_id}", response_model=StrategyTemplateResponse)
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager")),
) -> StrategyTemplateResponse:
    response = disable_strategy_template(db, template_id)
    create_audit_log(
        db,
        action="strategy_template_disabled",
        entity_type="strategy_template",
        entity_id=response.id,
        summary=f"Strategy template {response.strategy_code} disabled.",
        metadata={"template_id": response.id, "strategy_code": response.strategy_code},
        actor=current_user,
    )
    return response


@router.post("/{template_id}/candidate-prices", response_model=CandidatePriceResponse)
def create_candidate_prices_from_template(
    template_id: int,
    payload: StrategyTemplateCandidatePriceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> CandidatePriceResponse:
    response = apply_strategy_template_to_candidate_prices(db, template_id, payload)
    create_audit_log(
        db,
        action="strategy_template_candidate_prices_generated",
        entity_type="strategy_template",
        entity_id=template_id,
        summary=f"Candidate prices generated from strategy template {template_id}.",
        metadata={
            "template_id": template_id,
            "product_id": response.product_id,
            "quantity": response.quantity,
            "candidate_count": len(response.candidates),
        },
        actor=current_user,
    )
    return response


@router.post("/{template_id}/pricing-simulation", response_model=PricingSimulationResponse)
def create_pricing_simulation_from_template(
    template_id: int,
    payload: StrategyTemplatePricingSimulationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("viewer")),
) -> PricingSimulationResponse:
    response = apply_strategy_template_to_pricing_simulation(
        db, template_id, payload, current_user.username
    )
    create_audit_log(
        db,
        action="strategy_template_pricing_simulation_created",
        entity_type="strategy_template",
        entity_id=template_id,
        summary=f"Pricing simulation {response.id} created from strategy template {template_id}.",
        metadata={
            "template_id": template_id,
            "simulation_id": response.id,
            "product_id": response.product_id,
            "scenario_count": response.scenario_count,
        },
        actor=current_user,
    )
    return response
