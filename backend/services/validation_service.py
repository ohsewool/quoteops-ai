from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import CompetitorPrice, CostProfile, Product
from backend.schemas import (
    CompetitorContextResponse,
    PriceValidationCheck,
    PriceValidationRequest,
    PriceValidationResponse,
)


def validate_price(db: Session, payload: PriceValidationRequest) -> PriceValidationResponse:
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
    if payload.candidate_unit_price <= 0:
        raise HTTPException(
            status_code=400, detail="candidate_unit_price must be greater than 0"
        )
    if payload.minimum_margin_rate is not None and (
        payload.minimum_margin_rate < 0 or payload.minimum_margin_rate >= 1
    ):
        raise HTTPException(
            status_code=400,
            detail="minimum_margin_rate must be greater than or equal to 0 and less than 1",
        )

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

    unit_cost = (
        cost_profile.material_cost + cost_profile.labor_cost + cost_profile.overhead_cost
    )
    total_cost = unit_cost * payload.quantity
    candidate_total_price = payload.candidate_unit_price * payload.quantity
    estimated_gross_profit = candidate_total_price - total_cost
    estimated_margin_rate = estimated_gross_profit / candidate_total_price
    minimum_margin_rate = (
        payload.minimum_margin_rate
        if payload.minimum_margin_rate is not None
        else cost_profile.target_margin_rate
    )

    checks = [
        _price_above_unit_cost_check(payload.candidate_unit_price, unit_cost),
        _margin_meets_minimum_check(
            estimated_margin_rate, minimum_margin_rate, estimated_gross_profit
        ),
    ]

    competitor_context = None
    if payload.include_competitor_context:
        competitor_context = _build_competitor_context(db, product.id)
        checks.extend(
            _competitor_reference_checks(
                payload.candidate_unit_price, competitor_context
            )
        )

    validation_status = _validation_status(checks)
    risk_level = {
        "passed": "low",
        "warning": "medium",
        "failed": "high",
    }[validation_status]

    return PriceValidationResponse(
        product_id=product.id,
        product_name=product.name,
        quantity=payload.quantity,
        candidate_unit_price=_round_money(payload.candidate_unit_price),
        candidate_total_price=_round_money(candidate_total_price),
        unit_cost=_round_money(unit_cost),
        total_cost=_round_money(total_cost),
        estimated_gross_profit=_round_money(estimated_gross_profit),
        estimated_margin_rate=round(estimated_margin_rate, 4),
        minimum_margin_rate=round(minimum_margin_rate, 4),
        validation_status=validation_status,
        risk_level=risk_level,
        checks=checks,
        competitor_context=competitor_context,
        calculation_notes=[
            "Validation results are deterministic.",
            "No AI-generated validation decision was used.",
            "This result does not approve or activate the price.",
        ],
    )


def _price_above_unit_cost_check(
    candidate_unit_price: float, unit_cost: float
) -> PriceValidationCheck:
    passed = candidate_unit_price >= unit_cost
    return PriceValidationCheck(
        code="price_above_unit_cost",
        severity="error",
        passed=passed,
        message=(
            "Candidate price is above unit cost."
            if passed
            else "Candidate price is below unit cost."
        ),
    )


def _margin_meets_minimum_check(
    estimated_margin_rate: float,
    minimum_margin_rate: float,
    estimated_gross_profit: float,
) -> PriceValidationCheck:
    passed = estimated_margin_rate >= minimum_margin_rate
    severity = "error" if estimated_gross_profit < 0 else "warning"
    return PriceValidationCheck(
        code="margin_meets_minimum",
        severity=severity,
        passed=passed,
        message=(
            "Estimated margin meets the minimum margin threshold."
            if passed
            else "Estimated margin is below the minimum margin threshold."
        ),
    )


def _competitor_reference_checks(
    candidate_unit_price: float,
    competitor_context: CompetitorContextResponse,
) -> list[PriceValidationCheck]:
    if not competitor_context.available or competitor_context.average_reference_price is None:
        return []

    average_reference_price = competitor_context.average_reference_price
    below_threshold = average_reference_price * 0.8
    above_threshold = average_reference_price * 1.5
    below_passed = candidate_unit_price >= below_threshold
    above_passed = candidate_unit_price <= above_threshold
    return [
        PriceValidationCheck(
            code="competitor_reference_below_average",
            severity="warning",
            passed=below_passed,
            message=(
                "Candidate price is not far below the competitor average."
                if below_passed
                else "Candidate price is more than 20% below the competitor average."
            ),
        ),
        PriceValidationCheck(
            code="competitor_reference_above_average",
            severity="warning",
            passed=above_passed,
            message=(
                "Candidate price is not far above the competitor average."
                if above_passed
                else "Candidate price is more than 50% above the competitor average."
            ),
        ),
    ]


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


def _validation_status(checks: list[PriceValidationCheck]) -> str:
    if any(check.severity == "error" and not check.passed for check in checks):
        return "failed"
    if any(check.severity == "warning" and not check.passed for check in checks):
        return "warning"
    return "passed"


def _round_money(value: float) -> float:
    return round(value, 2)
