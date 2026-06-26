from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import CompetitorPrice, CostProfile, Product
from backend.schemas import (
    CandidatePriceOption,
    CandidatePriceRequest,
    CandidatePriceResponse,
    CompetitorContextResponse,
)


DEFAULT_MARGIN_RATES = [0.25, 0.35, 0.45]
DEFAULT_STRATEGIES = ["low_margin", "target_margin", "premium_margin"]


def generate_candidate_prices(
    db: Session, payload: CandidatePriceRequest
) -> CandidatePriceResponse:
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")

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
        raise HTTPException(status_code=400, detail="Active cost profile not found")

    margin_rates = payload.margin_rates or DEFAULT_MARGIN_RATES
    _validate_margin_rates(margin_rates)

    unit_cost = (
        cost_profile.material_cost + cost_profile.labor_cost + cost_profile.overhead_cost
    )
    total_cost = unit_cost * payload.quantity
    candidates = [
        _build_candidate(strategy, unit_cost, total_cost, payload.quantity, margin_rate)
        for strategy, margin_rate in _strategy_margin_pairs(margin_rates)
    ]

    competitor_context = None
    if payload.include_competitor_context:
        competitor_context = _build_competitor_context(db, product.id)

    return CandidatePriceResponse(
        product_id=product.id,
        product_name=product.name,
        quantity=payload.quantity,
        unit_cost=_round_money(unit_cost),
        total_cost=_round_money(total_cost),
        candidates=candidates,
        competitor_context=competitor_context,
        calculation_notes=[
            "Candidate prices are deterministic.",
            "Competitor prices are manually entered reference data.",
            "No AI-generated price was used.",
        ],
    )


def _validate_margin_rates(margin_rates: list[float]) -> None:
    if not margin_rates:
        raise HTTPException(status_code=400, detail="At least one margin rate is required")
    for margin_rate in margin_rates:
        if margin_rate < 0 or margin_rate >= 1:
            raise HTTPException(
                status_code=400,
                detail="margin_rates must be greater than or equal to 0 and less than 1",
            )


def _strategy_margin_pairs(margin_rates: list[float]) -> list[tuple[str, float]]:
    if margin_rates == DEFAULT_MARGIN_RATES:
        return list(zip(DEFAULT_STRATEGIES, margin_rates))
    return [
        (f"custom_margin_{index}", margin_rate)
        for index, margin_rate in enumerate(margin_rates, start=1)
    ]


def _build_candidate(
    strategy: str,
    unit_cost: float,
    total_cost: float,
    quantity: int,
    margin_rate: float,
) -> CandidatePriceOption:
    unit_price = unit_cost / (1 - margin_rate)
    total_price = unit_price * quantity
    estimated_gross_profit = total_price - total_cost
    estimated_margin_rate = (
        estimated_gross_profit / total_price if total_price > 0 else 0.0
    )
    return CandidatePriceOption(
        strategy=strategy,
        margin_rate=round(margin_rate, 4),
        unit_price=_round_money(unit_price),
        total_price=_round_money(total_price),
        estimated_gross_profit=_round_money(estimated_gross_profit),
        estimated_margin_rate=round(estimated_margin_rate, 4),
        notes=[
            "Deterministic candidate generated from unit cost and margin rate.",
            "No AI-generated price was used.",
        ],
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
