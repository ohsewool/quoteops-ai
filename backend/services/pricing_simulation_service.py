import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import (
    CompetitorPrice,
    CostProfile,
    PricingSimulation,
    PricingSimulationScenario,
    Product,
)
from backend.schemas import (
    CompetitorContextResponse,
    PricingSimulationCreate,
    PricingSimulationResponse,
    PricingSimulationScenarioResponse,
)


MAX_SCENARIOS = 100
SIMULATION_NOTES = [
    "Simulation results are deterministic.",
    "No AI-generated price was used.",
    "Simulation does not approve or activate any price.",
]


def create_pricing_simulation(
    db: Session, payload: PricingSimulationCreate, created_by_username: str
) -> PricingSimulationResponse:
    _validate_inputs(payload)
    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    cost_profile = (
        db.query(CostProfile)
        .filter(CostProfile.product_id == product.id, CostProfile.active.is_(True))
        .order_by(CostProfile.id.desc())
        .first()
    )
    if cost_profile is None:
        raise HTTPException(status_code=404, detail="Active cost profile not found")

    unit_cost = _round_money(
        cost_profile.material_cost + cost_profile.labor_cost + cost_profile.overhead_cost
    )
    competitor_context = (
        _build_competitor_context(db, product.id)
        if payload.include_competitor_context
        else None
    )
    simulation = PricingSimulation(
        name=payload.name,
        product_id=product.id,
        unit_cost=unit_cost,
        include_competitor_context=payload.include_competitor_context,
        competitor_context_json=(
            competitor_context.model_dump_json() if competitor_context is not None else None
        ),
        notes=payload.notes,
        created_by_username=created_by_username,
    )
    db.add(simulation)
    db.flush()

    for quantity in payload.quantities:
        for margin_rate in payload.margin_rates:
            db.add(_build_scenario(simulation.id, unit_cost, quantity, margin_rate))

    db.commit()
    db.refresh(simulation)
    return _to_response(simulation)


def list_pricing_simulations(db: Session) -> list[PricingSimulationResponse]:
    simulations = db.query(PricingSimulation).order_by(PricingSimulation.id.desc()).all()
    return [_to_response(simulation) for simulation in simulations]


def get_pricing_simulation(db: Session, simulation_id: int) -> PricingSimulationResponse:
    simulation = db.get(PricingSimulation, simulation_id)
    if simulation is None:
        raise HTTPException(status_code=404, detail="Pricing simulation not found")
    return _to_response(simulation)


def _validate_inputs(payload: PricingSimulationCreate) -> None:
    if not payload.quantities:
        raise HTTPException(status_code=400, detail="quantities must not be empty")
    if not payload.margin_rates:
        raise HTTPException(status_code=400, detail="margin_rates must not be empty")
    if len(payload.quantities) * len(payload.margin_rates) > MAX_SCENARIOS:
        raise HTTPException(status_code=400, detail="Scenario count exceeds safe maximum")
    if any(quantity <= 0 for quantity in payload.quantities):
        raise HTTPException(status_code=400, detail="Each quantity must be greater than 0")
    if any(margin_rate < 0 or margin_rate >= 1 for margin_rate in payload.margin_rates):
        raise HTTPException(status_code=400, detail="Each margin rate must be >= 0 and < 1")


def _build_scenario(
    simulation_id: int, unit_cost: float, quantity: int, margin_rate: float
) -> PricingSimulationScenario:
    unit_price = unit_cost / (1 - margin_rate)
    total_price = unit_price * quantity
    total_cost = unit_cost * quantity
    estimated_gross_profit = total_price - total_cost
    estimated_margin_rate = estimated_gross_profit / total_price if total_price > 0 else 0.0
    validation_status = "passed" if unit_price >= unit_cost else "failed"
    risk_level = "low" if validation_status == "passed" else "high"
    return PricingSimulationScenario(
        simulation_id=simulation_id,
        quantity=quantity,
        margin_rate=round(margin_rate, 4),
        unit_price=_round_money(unit_price),
        total_price=_round_money(total_price),
        total_cost=_round_money(total_cost),
        estimated_gross_profit=_round_money(estimated_gross_profit),
        estimated_margin_rate=round(estimated_margin_rate, 4),
        validation_status=validation_status,
        risk_level=risk_level,
    )


def _build_competitor_context(db: Session, product_id: int) -> CompetitorContextResponse:
    prices = [
        row.reference_price
        for row in db.query(CompetitorPrice)
        .filter(CompetitorPrice.product_id == product_id)
        .order_by(CompetitorPrice.id)
        .all()
    ]
    if not prices:
        return CompetitorContextResponse(available=False, reference_price_count=0)
    return CompetitorContextResponse(
        available=True,
        reference_price_count=len(prices),
        min_reference_price=_round_money(min(prices)),
        max_reference_price=_round_money(max(prices)),
        average_reference_price=_round_money(sum(prices) / len(prices)),
    )


def _to_response(simulation: PricingSimulation) -> PricingSimulationResponse:
    competitor_context = None
    if simulation.competitor_context_json:
        competitor_context = CompetitorContextResponse(**json.loads(simulation.competitor_context_json))
    scenarios = [
        PricingSimulationScenarioResponse.model_validate(scenario)
        for scenario in sorted(simulation.scenarios, key=lambda item: item.id)
    ]
    return PricingSimulationResponse(
        id=simulation.id,
        name=simulation.name,
        product_id=simulation.product_id,
        product_name=simulation.product.name,
        unit_cost=simulation.unit_cost,
        include_competitor_context=simulation.include_competitor_context,
        scenario_count=len(scenarios),
        scenarios=scenarios,
        competitor_context=competitor_context,
        notes=simulation.notes,
        created_by_username=simulation.created_by_username,
        created_at=simulation.created_at,
        simulation_notes=SIMULATION_NOTES,
    )


def _round_money(value: float) -> float:
    return round(value, 2)
