import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import PricingStrategyTemplate
from backend.schemas import (
    CandidatePriceRequest,
    CandidatePriceResponse,
    PricingSimulationCreate,
    PricingSimulationResponse,
    StrategyTemplateCandidatePriceRequest,
    StrategyTemplateCreate,
    StrategyTemplatePricingSimulationRequest,
    StrategyTemplateResponse,
    StrategyTemplateUpdate,
)
from backend.services.candidate_price_service import generate_candidate_prices
from backend.services.pricing_simulation_service import create_pricing_simulation


def create_strategy_template(
    db: Session, payload: StrategyTemplateCreate, created_by_username: str
) -> StrategyTemplateResponse:
    _ensure_unique_strategy_code(db, payload.strategy_code)
    template = PricingStrategyTemplate(
        name=payload.name,
        strategy_code=payload.strategy_code,
        description=payload.description,
        margin_rates_json=_dump_json(payload.margin_rates),
        default_quantities_json=_dump_json(payload.default_quantities),
        include_competitor_context_default=payload.include_competitor_context_default,
        risk_preference=payload.risk_preference,
        active=payload.active,
        notes=payload.notes,
        created_by_username=created_by_username,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return _to_response(template)


def list_strategy_templates(db: Session) -> list[StrategyTemplateResponse]:
    templates = db.query(PricingStrategyTemplate).order_by(PricingStrategyTemplate.id).all()
    return [_to_response(template) for template in templates]


def get_strategy_template(db: Session, template_id: int) -> StrategyTemplateResponse:
    return _to_response(_get_template(db, template_id))


def update_strategy_template(
    db: Session, template_id: int, payload: StrategyTemplateUpdate
) -> StrategyTemplateResponse:
    template = _get_template(db, template_id)
    if payload.strategy_code is not None and payload.strategy_code != template.strategy_code:
        _ensure_unique_strategy_code(db, payload.strategy_code)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "margin_rates":
            template.margin_rates_json = _dump_json(value)
        elif field == "default_quantities":
            template.default_quantities_json = _dump_json(value)
        else:
            setattr(template, field, value)

    db.commit()
    db.refresh(template)
    return _to_response(template)


def disable_strategy_template(db: Session, template_id: int) -> StrategyTemplateResponse:
    template = _get_template(db, template_id)
    template.active = False
    db.commit()
    db.refresh(template)
    return _to_response(template)


def apply_strategy_template_to_candidate_prices(
    db: Session, template_id: int, payload: StrategyTemplateCandidatePriceRequest
) -> CandidatePriceResponse:
    template = _get_active_template(db, template_id)
    include_competitor_context = (
        template.include_competitor_context_default
        if payload.include_competitor_context is None
        else payload.include_competitor_context
    )
    return generate_candidate_prices(
        db,
        CandidatePriceRequest(
            product_id=payload.product_id,
            quantity=payload.quantity,
            margin_rates=_load_margin_rates(template),
            include_competitor_context=include_competitor_context,
        ),
    )


def apply_strategy_template_to_pricing_simulation(
    db: Session,
    template_id: int,
    payload: StrategyTemplatePricingSimulationRequest,
    created_by_username: str,
) -> PricingSimulationResponse:
    template = _get_active_template(db, template_id)
    include_competitor_context = (
        template.include_competitor_context_default
        if payload.include_competitor_context is None
        else payload.include_competitor_context
    )
    return create_pricing_simulation(
        db,
        PricingSimulationCreate(
            name=payload.name,
            product_id=payload.product_id,
            quantities=payload.quantities or _load_default_quantities(template),
            margin_rates=_load_margin_rates(template),
            include_competitor_context=include_competitor_context,
            notes=payload.notes
            or f"Created from strategy template {template.strategy_code}.",
        ),
        created_by_username,
    )


def _get_template(db: Session, template_id: int) -> PricingStrategyTemplate:
    template = db.get(PricingStrategyTemplate, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Strategy template not found")
    return template


def _get_active_template(db: Session, template_id: int) -> PricingStrategyTemplate:
    template = _get_template(db, template_id)
    if not template.active:
        raise HTTPException(status_code=400, detail="Strategy template is inactive")
    return template


def _ensure_unique_strategy_code(
    db: Session, strategy_code: str, template_id: int | None = None
) -> None:
    query = db.query(PricingStrategyTemplate).filter(
        PricingStrategyTemplate.strategy_code == strategy_code
    )
    if template_id is not None:
        query = query.filter(PricingStrategyTemplate.id != template_id)
    if query.first() is not None:
        raise HTTPException(status_code=400, detail="strategy_code must be unique")


def _to_response(template: PricingStrategyTemplate) -> StrategyTemplateResponse:
    return StrategyTemplateResponse(
        id=template.id,
        name=template.name,
        strategy_code=template.strategy_code,
        description=template.description,
        margin_rates=_load_margin_rates(template),
        default_quantities=_load_default_quantities(template),
        include_competitor_context_default=template.include_competitor_context_default,
        risk_preference=template.risk_preference,
        active=template.active,
        notes=template.notes,
        created_by_username=template.created_by_username,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def _dump_json(value: list[float] | list[int]) -> str:
    return json.dumps(value, separators=(",", ":"))


def _load_margin_rates(template: PricingStrategyTemplate) -> list[float]:
    return [float(item) for item in json.loads(template.margin_rates_json)]


def _load_default_quantities(template: PricingStrategyTemplate) -> list[int]:
    return [int(item) for item in json.loads(template.default_quantities_json)]
