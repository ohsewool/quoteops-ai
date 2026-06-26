from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import CostProfile, Product
from backend.schemas import QuotePreviewRequest, QuotePreviewResponse


def calculate_quote_preview(
    db: Session, payload: QuotePreviewRequest
) -> QuotePreviewResponse:
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

    material_cost = _resolve_cost("material_cost", payload.material_cost, cost_profile)
    labor_cost = _resolve_cost("labor_cost", payload.labor_cost, cost_profile)
    overhead_cost = _resolve_cost("overhead_cost", payload.overhead_cost, cost_profile)
    target_margin_rate = _resolve_margin(payload.target_margin_rate, cost_profile)

    unit_cost = material_cost + labor_cost + overhead_cost
    suggested_unit_price = unit_cost / (1 - target_margin_rate)
    total_cost = unit_cost * payload.quantity
    suggested_total_price = suggested_unit_price * payload.quantity
    estimated_gross_profit = suggested_total_price - total_cost
    estimated_margin_rate = (
        estimated_gross_profit / suggested_total_price
        if suggested_total_price > 0
        else 0.0
    )

    return QuotePreviewResponse(
        product_id=product.id,
        product_name=product.name,
        quantity=payload.quantity,
        unit_cost=_round_money(unit_cost),
        total_cost=_round_money(total_cost),
        target_margin_rate=round(target_margin_rate, 4),
        suggested_unit_price=_round_money(suggested_unit_price),
        suggested_total_price=_round_money(suggested_total_price),
        estimated_gross_profit=_round_money(estimated_gross_profit),
        estimated_margin_rate=round(estimated_margin_rate, 4),
        calculation_notes=[
            "Calculated deterministically from cost inputs and target margin.",
            "No AI-generated price was used.",
        ],
    )


def _resolve_cost(
    field_name: str, override_value: float | None, cost_profile: CostProfile | None
) -> float:
    value = override_value
    if value is None and cost_profile is not None:
        value = getattr(cost_profile, field_name)
    if value is None:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name} is required when no active cost profile exists",
        )
    if value < 0:
        raise HTTPException(status_code=400, detail=f"{field_name} must be at least 0")
    return value


def _resolve_margin(
    override_value: float | None, cost_profile: CostProfile | None
) -> float:
    value = override_value
    if value is None and cost_profile is not None:
        value = cost_profile.target_margin_rate
    if value is None:
        raise HTTPException(
            status_code=400,
            detail="target_margin_rate is required when no active cost profile exists",
        )
    if value < 0 or value >= 1:
        raise HTTPException(
            status_code=400,
            detail="target_margin_rate must be greater than or equal to 0 and less than 1",
        )
    return value


def _round_money(value: float) -> float:
    return round(value, 2)
