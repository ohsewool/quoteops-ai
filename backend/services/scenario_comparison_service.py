import json

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import (
    CompetitorPrice,
    CostProfile,
    Product,
    ScenarioComparison,
    ScenarioComparisonItem,
)
from backend.schemas import (
    CompetitorContextResponse,
    PriceValidationRequest,
    ScenarioComparisonCreate,
    ScenarioComparisonItemResponse,
    ScenarioComparisonResponse,
    ScenarioComparisonScenarioInput,
    ScenarioComparisonSummary,
)
from backend.services.validation_service import validate_price


MAX_SCENARIOS = 50
COMPARISON_NOTES = [
    "Scenario comparison is deterministic.",
    "This comparison does not approve or activate any price.",
    "Human review is still required before using any scenario for customer pricing.",
]
SCENARIO_NOTES = [
    "Scenario calculated deterministically.",
    "No AI-generated price was used.",
    "Validation status and risk level are deterministic.",
]
RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def create_scenario_comparison(
    db: Session, payload: ScenarioComparisonCreate, created_by_username: str
) -> ScenarioComparisonResponse:
    _validate_payload(payload)

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
    built_items = [
        _build_item(db, payload.product_id, unit_cost, scenario, index)
        for index, scenario in enumerate(payload.scenarios, start=1)
    ]
    summary = _build_summary(built_items)
    competitor_context = (
        _build_competitor_context(db, product.id)
        if payload.include_competitor_context
        else None
    )

    comparison = ScenarioComparison(
        name=payload.name,
        description=payload.description,
        product_id=product.id,
        created_by_username=created_by_username,
        summary_json=summary.model_dump_json(),
        competitor_context_json=(
            competitor_context.model_dump_json() if competitor_context is not None else None
        ),
    )
    db.add(comparison)
    db.flush()

    for item_data in built_items:
        db.add(
            ScenarioComparisonItem(
                comparison_id=comparison.id,
                label=item_data["label"],
                source_type="direct",
                source_id=None,
                quantity=item_data["quantity"],
                margin_rate=item_data["margin_rate"],
                unit_cost=item_data["unit_cost"],
                unit_price=item_data["unit_price"],
                total_cost=item_data["total_cost"],
                total_price=item_data["total_price"],
                estimated_gross_profit=item_data["estimated_gross_profit"],
                estimated_margin_rate=item_data["estimated_margin_rate"],
                validation_status=item_data["validation_status"],
                risk_level=item_data["risk_level"],
                notes_json=json.dumps(SCENARIO_NOTES, separators=(",", ":")),
            )
        )

    db.commit()
    db.refresh(comparison)
    return _to_response(comparison)


def list_scenario_comparisons(db: Session) -> list[ScenarioComparisonResponse]:
    comparisons = db.query(ScenarioComparison).order_by(ScenarioComparison.id.desc()).all()
    return [_to_response(comparison) for comparison in comparisons]


def get_scenario_comparison(db: Session, comparison_id: int) -> ScenarioComparisonResponse:
    comparison = db.get(ScenarioComparison, comparison_id)
    if comparison is None:
        raise HTTPException(status_code=404, detail="Scenario comparison not found")
    return _to_response(comparison)


def _validate_payload(payload: ScenarioComparisonCreate) -> None:
    if not payload.scenarios:
        raise HTTPException(status_code=400, detail="scenarios must not be empty")
    if len(payload.scenarios) > MAX_SCENARIOS:
        raise HTTPException(status_code=400, detail="Scenario count exceeds safe maximum")
    for scenario in payload.scenarios:
        if scenario.quantity <= 0:
            raise HTTPException(status_code=400, detail="Each quantity must be greater than 0")
        if scenario.margin_rate < 0 or scenario.margin_rate >= 1:
            raise HTTPException(status_code=400, detail="Each margin rate must be >= 0 and < 1")


def _build_item(
    db: Session,
    product_id: int,
    unit_cost: float,
    scenario: ScenarioComparisonScenarioInput,
    index: int,
) -> dict:
    label = (scenario.label or "").strip() or f"Scenario {index}"
    unit_price = unit_cost / (1 - scenario.margin_rate)
    total_cost = unit_cost * scenario.quantity
    total_price = unit_price * scenario.quantity
    estimated_gross_profit = total_price - total_cost
    estimated_margin_rate = estimated_gross_profit / total_price if total_price > 0 else 0.0
    validation = validate_price(
        db,
        PriceValidationRequest(
            product_id=product_id,
            quantity=scenario.quantity,
            candidate_unit_price=unit_price,
        ),
    )
    return {
        "label": label,
        "quantity": scenario.quantity,
        "margin_rate": round(scenario.margin_rate, 4),
        "unit_cost": _round_money(unit_cost),
        "unit_price": _round_money(unit_price),
        "total_cost": _round_money(total_cost),
        "total_price": _round_money(total_price),
        "estimated_gross_profit": _round_money(estimated_gross_profit),
        "estimated_margin_rate": round(estimated_margin_rate, 4),
        "validation_status": validation.validation_status,
        "risk_level": validation.risk_level,
    }


def _build_summary(items: list[dict]) -> ScenarioComparisonSummary:
    highest_margin = max(items, key=lambda item: item["estimated_margin_rate"])
    highest_profit = max(items, key=lambda item: item["estimated_gross_profit"])
    lowest_risk = min(items, key=lambda item: RISK_ORDER.get(item["risk_level"], 99))
    lowest_unit_price = min(items, key=lambda item: item["unit_price"])
    highest_unit_price = max(items, key=lambda item: item["unit_price"])
    highest_total_price = max(items, key=lambda item: item["total_price"])
    unit_prices = [item["unit_price"] for item in items]
    gross_profits = [item["estimated_gross_profit"] for item in items]
    risk_distribution = {"low": 0, "medium": 0, "high": 0}
    for item in items:
        risk_distribution[item["risk_level"]] = risk_distribution.get(item["risk_level"], 0) + 1
    return ScenarioComparisonSummary(
        highest_margin_label=highest_margin["label"],
        highest_profit_label=highest_profit["label"],
        lowest_risk_label=lowest_risk["label"],
        lowest_unit_price_label=lowest_unit_price["label"],
        highest_unit_price_label=highest_unit_price["label"],
        highest_total_price_label=highest_total_price["label"],
        unit_price_range=_round_money(max(unit_prices) - min(unit_prices)),
        gross_profit_range=_round_money(max(gross_profits) - min(gross_profits)),
        risk_distribution=risk_distribution,
    )


def _to_response(comparison: ScenarioComparison) -> ScenarioComparisonResponse:
    summary = ScenarioComparisonSummary(**json.loads(comparison.summary_json))
    competitor_context = None
    if comparison.competitor_context_json:
        competitor_context = CompetitorContextResponse(
            **json.loads(comparison.competitor_context_json)
        )
    scenarios = [
        ScenarioComparisonItemResponse(
            id=item.id,
            comparison_id=item.comparison_id,
            label=item.label,
            source_type=item.source_type,
            source_id=item.source_id,
            quantity=item.quantity,
            margin_rate=item.margin_rate,
            unit_cost=item.unit_cost,
            unit_price=item.unit_price,
            total_cost=item.total_cost,
            total_price=item.total_price,
            estimated_gross_profit=item.estimated_gross_profit,
            estimated_margin_rate=item.estimated_margin_rate,
            validation_status=item.validation_status,
            risk_level=item.risk_level,
            notes=json.loads(item.notes_json),
            created_at=item.created_at,
        )
        for item in sorted(comparison.items, key=lambda row: row.id)
    ]
    return ScenarioComparisonResponse(
        id=comparison.id,
        name=comparison.name,
        description=comparison.description,
        product_id=comparison.product_id,
        product_name=comparison.product.name,
        scenario_count=len(scenarios),
        summary=summary,
        scenarios=scenarios,
        competitor_context=competitor_context,
        comparison_notes=COMPARISON_NOTES,
        created_by_username=comparison.created_by_username,
        created_at=comparison.created_at,
        updated_at=comparison.updated_at,
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


def _round_money(value: float) -> float:
    return round(value, 2)
