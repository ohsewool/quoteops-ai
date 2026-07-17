from decimal import Decimal

import pytest

from backend.domain.pricing import RiskLevel, ValidationStatus
from backend.services.pricing_engine import PricingLineInput, calculate_candidate, calculate_candidate_line, validate_candidate


def test_candidate_formula_uses_exact_decimal_and_independent_saved_rounding() -> None:
    line = calculate_candidate_line(
        quantity=25,
        material_cost=Decimal("1000.00"),
        labor_cost=Decimal("500.00"),
        overhead_cost=Decimal("500.00"),
        margin_rate=Decimal("0.350000"),
    )
    assert line.unit_cost == Decimal("2000.00")
    assert line.unit_price == Decimal("3076.92")
    assert line.total_cost == Decimal("50000.00")
    assert line.total_price == Decimal("76923.08")

    candidate = calculate_candidate(
        [PricingLineInput(quantity=25, material_cost=Decimal("1000"), labor_cost=Decimal("500"), overhead_cost=Decimal("500"))],
        margin_rate=Decimal("0.350000"),
    )
    assert candidate.gross_profit == Decimal("26923.08")
    assert candidate.margin_rate == Decimal("0.350000")


def test_validation_maps_error_to_blocked_risk_and_market_gap_to_warning() -> None:
    candidate = calculate_candidate(
        [PricingLineInput(quantity=10, material_cost=Decimal("100"), labor_cost=Decimal("0"), overhead_cost=Decimal("0"))],
        margin_rate=Decimal("0.250000"),
    )
    blocked = validate_candidate(
        candidate,
        minimum_margin_rate=Decimal("0.350000"),
        competitor_average_unit_price=None,
        competitor_context_included=False,
    )
    assert blocked.status is ValidationStatus.FAILED
    assert blocked.risk_level is RiskLevel.HIGH
    assert next(check for check in blocked.checks if check.code == "minimum_margin").passed is False

    warning = validate_candidate(
        candidate,
        minimum_margin_rate=Decimal("0.250000"),
        competitor_average_unit_price=Decimal("1000.00"),
        competitor_context_included=True,
    )
    assert warning.status is ValidationStatus.WARNING
    assert warning.risk_level is RiskLevel.MEDIUM
    assert next(check for check in warning.checks if check.code == "market_floor").passed is False


def test_engine_rejects_invalid_quantities_margins_and_binary_float() -> None:
    with pytest.raises(ValueError, match="Quantity must be positive"):
        calculate_candidate_line(
            quantity=0,
            material_cost="1",
            labor_cost="0",
            overhead_cost="0",
            margin_rate="0.25",
        )
    with pytest.raises(ValueError, match="less than 1"):
        calculate_candidate_line(
            quantity=1,
            material_cost="1",
            labor_cost="0",
            overhead_cost="0",
            margin_rate="1",
        )
    with pytest.raises(TypeError, match="Binary float"):
        calculate_candidate_line(
            quantity=1,
            material_cost=1.0,
            labor_cost="0",
            overhead_cost="0",
            margin_rate="0.25",
        )
