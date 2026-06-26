from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.models import PriceApprovalRequest, Product
from backend.schemas import QuoteExplanationRequest, QuoteExplanationResponse


VALIDATION_STATUSES = {"passed", "warning", "failed"}
RISK_LEVELS = {"low", "medium", "high"}
EXPLANATION_STYLES = {"concise", "detailed", "manager"}


def explain_quote(
    db: Session, payload: QuoteExplanationRequest
) -> QuoteExplanationResponse:
    if payload.approval_request_id is not None:
        if _has_direct_pricing_fields(payload):
            raise HTTPException(
                status_code=400,
                detail="approval_request_id cannot be combined with direct pricing fields",
            )
        return _explain_approval_snapshot(db, payload)

    return _explain_direct_fields(db, payload)


def _explain_approval_snapshot(
    db: Session, payload: QuoteExplanationRequest
) -> QuoteExplanationResponse:
    approval_request = db.get(PriceApprovalRequest, payload.approval_request_id)
    if approval_request is None:
        raise HTTPException(status_code=404, detail="Approval request not found")
    style = _resolve_style(payload.explanation_style)
    return _build_response(
        product_id=approval_request.product_id,
        product_name=approval_request.product.name,
        quantity=approval_request.quantity,
        unit_cost=approval_request.unit_cost,
        proposed_unit_price=approval_request.proposed_unit_price,
        estimated_margin_rate=approval_request.estimated_margin_rate,
        validation_status=approval_request.validation_status,
        risk_level=approval_request.risk_level,
        style=style,
        audience=payload.explanation_audience,
    )


def _explain_direct_fields(
    db: Session, payload: QuoteExplanationRequest
) -> QuoteExplanationResponse:
    _require_direct_fields(payload)
    _validate_direct_values(payload)

    product = db.get(Product, payload.product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    style = _resolve_style(payload.explanation_style)
    proposed_unit_price = (
        payload.proposed_unit_price
        if payload.proposed_unit_price is not None
        else payload.candidate_unit_price
    )
    return _build_response(
        product_id=product.id,
        product_name=product.name,
        quantity=payload.quantity,
        unit_cost=payload.unit_cost,
        proposed_unit_price=proposed_unit_price,
        estimated_margin_rate=payload.estimated_margin_rate,
        validation_status=payload.validation_status,
        risk_level=payload.risk_level,
        style=style,
        audience=payload.explanation_audience,
    )


def _require_direct_fields(payload: QuoteExplanationRequest) -> None:
    required_values = {
        "product_id": payload.product_id,
        "quantity": payload.quantity,
        "unit_cost": payload.unit_cost,
        "estimated_margin_rate": payload.estimated_margin_rate,
        "validation_status": payload.validation_status,
        "risk_level": payload.risk_level,
    }
    missing_fields = [field for field, value in required_values.items() if value is None]
    if payload.proposed_unit_price is None and payload.candidate_unit_price is None:
        missing_fields.append("proposed_unit_price")
    if missing_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required direct pricing fields: {', '.join(missing_fields)}",
        )


def _validate_direct_values(payload: QuoteExplanationRequest) -> None:
    proposed_unit_price = (
        payload.proposed_unit_price
        if payload.proposed_unit_price is not None
        else payload.candidate_unit_price
    )
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
    if payload.unit_cost < 0:
        raise HTTPException(status_code=400, detail="unit_cost must be at least 0")
    if proposed_unit_price <= 0:
        raise HTTPException(
            status_code=400, detail="proposed_unit_price must be greater than 0"
        )
    if payload.estimated_margin_rate < -1 or payload.estimated_margin_rate > 1:
        raise HTTPException(
            status_code=400, detail="estimated_margin_rate must be between -1 and 1"
        )
    if payload.validation_status not in VALIDATION_STATUSES:
        raise HTTPException(status_code=400, detail="Unsupported validation_status")
    if payload.risk_level not in RISK_LEVELS:
        raise HTTPException(status_code=400, detail="Unsupported risk_level")


def _resolve_style(style: str | None) -> str:
    resolved_style = style or "concise"
    if resolved_style not in EXPLANATION_STYLES:
        raise HTTPException(status_code=400, detail="Unsupported explanation_style")
    return resolved_style


def _build_response(
    product_id: int,
    product_name: str,
    quantity: int,
    unit_cost: float,
    proposed_unit_price: float,
    estimated_margin_rate: float,
    validation_status: str,
    risk_level: str,
    style: str,
    audience: str | None,
) -> QuoteExplanationResponse:
    margin_percent = round(estimated_margin_rate * 100, 2)
    summary = _summary(validation_status, risk_level, proposed_unit_price, unit_cost)
    bullets = [
        _price_position_bullet(proposed_unit_price, unit_cost),
        f"The estimated margin is approximately {margin_percent}%.",
        f"The validation status is {validation_status} and the risk level is {risk_level}.",
        "This explanation does not approve or activate the price.",
    ]
    if style in {"detailed", "manager"}:
        bullets.insert(
            3,
            f"The quote covers {quantity} unit(s) of {product_name} for human review.",
        )
    if style == "manager":
        bullets.append("A manager should confirm customer context and business fit.")
    if audience:
        bullets.append(f"This explanation is written for a {audience} audience.")

    return QuoteExplanationResponse(
        product_id=product_id,
        product_name=product_name,
        quantity=quantity,
        unit_cost=round(unit_cost, 2),
        proposed_unit_price=round(proposed_unit_price, 2),
        estimated_margin_rate=round(estimated_margin_rate, 4),
        validation_status=validation_status,
        risk_level=risk_level,
        explanation_summary=summary,
        explanation_bullets=bullets,
        decision_boundaries=[
            "No price was generated by AI.",
            "No approval decision was made by AI.",
            "A human reviewer must still approve or reject the quote.",
        ],
        explanation_source="deterministic_template",
    )


def _summary(
    validation_status: str,
    risk_level: str,
    proposed_unit_price: float,
    unit_cost: float,
) -> str:
    if validation_status == "passed" and risk_level == "low":
        return (
            "This quote appears financially safe because the proposed unit price is "
            "above unit cost and the validation result is passed."
        )
    if validation_status == "warning":
        return (
            "This quote needs human review because deterministic validation produced "
            "a warning even though the proposed price may still be usable."
        )
    if proposed_unit_price < unit_cost or validation_status == "failed":
        return (
            "This quote appears risky because deterministic validation failed or the "
            "proposed price may not safely cover cost."
        )
    return (
        "This quote should be reviewed by a human before any customer-facing or "
        "approval action is taken."
    )


def _price_position_bullet(proposed_unit_price: float, unit_cost: float) -> str:
    if proposed_unit_price >= unit_cost:
        return "The proposed unit price is higher than or equal to the calculated unit cost."
    return "The proposed unit price is lower than the calculated unit cost."


def _has_direct_pricing_fields(payload: QuoteExplanationRequest) -> bool:
    return any(
        value is not None
        for value in (
            payload.product_id,
            payload.quantity,
            payload.unit_cost,
            payload.proposed_unit_price,
            payload.candidate_unit_price,
            payload.estimated_margin_rate,
            payload.validation_status,
            payload.risk_level,
        )
    )
