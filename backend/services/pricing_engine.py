"""Pure Decimal pricing and validation functions for V2 pricing checks."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from backend.domain.money import decimal_string, quantize_money, quantize_rate, to_decimal
from backend.domain.pricing import RiskLevel, ValidationSeverity, ValidationStatus


@dataclass(frozen=True)
class PricingLineInput:
    quantity: int
    material_cost: Decimal
    labor_cost: Decimal
    overhead_cost: Decimal


@dataclass(frozen=True)
class CalculatedCandidateLine:
    quantity: int
    unit_cost_raw: Decimal
    unit_price_raw: Decimal
    total_cost_raw: Decimal
    total_price_raw: Decimal
    unit_cost: Decimal
    unit_price: Decimal
    total_cost: Decimal
    total_price: Decimal


@dataclass(frozen=True)
class CalculatedCandidate:
    lines: tuple[CalculatedCandidateLine, ...]
    total_cost_raw: Decimal
    total_price_raw: Decimal
    gross_profit_raw: Decimal
    margin_rate_raw: Decimal
    total_cost: Decimal
    total_price: Decimal
    gross_profit: Decimal
    margin_rate: Decimal
    average_unit_price_raw: Decimal


@dataclass(frozen=True)
class ValidationCheckCalculation:
    code: str
    severity: ValidationSeverity
    passed: bool
    message: str
    details: dict[str, object]


@dataclass(frozen=True)
class CandidateValidation:
    status: ValidationStatus
    risk_level: RiskLevel
    checks: tuple[ValidationCheckCalculation, ...]


def _exact_decimal(value: Decimal | int | str) -> Decimal:
    return to_decimal(value)


def calculate_candidate_line(
    *,
    quantity: int,
    material_cost: Decimal | int | str,
    labor_cost: Decimal | int | str,
    overhead_cost: Decimal | int | str,
    margin_rate: Decimal | int | str,
) -> CalculatedCandidateLine:
    """Calculate one priceable line without using binary float arithmetic."""

    if quantity <= 0:
        raise ValueError("Quantity must be positive")
    material = _exact_decimal(material_cost)
    labor = _exact_decimal(labor_cost)
    overhead = _exact_decimal(overhead_cost)
    margin = _exact_decimal(margin_rate)
    if min(material, labor, overhead) < 0:
        raise ValueError("Cost components must be non-negative")
    if margin < 0 or margin >= 1:
        raise ValueError("Margin rate must be greater than or equal to 0 and less than 1")

    unit_cost_raw = material + labor + overhead
    unit_price_raw = unit_cost_raw / (Decimal("1") - margin)
    total_cost_raw = unit_cost_raw * quantity
    total_price_raw = unit_price_raw * quantity
    return CalculatedCandidateLine(
        quantity=quantity,
        unit_cost_raw=unit_cost_raw,
        unit_price_raw=unit_price_raw,
        total_cost_raw=total_cost_raw,
        total_price_raw=total_price_raw,
        unit_cost=quantize_money(unit_cost_raw),
        unit_price=quantize_money(unit_price_raw),
        total_cost=quantize_money(total_cost_raw),
        total_price=quantize_money(total_price_raw),
    )


def calculate_candidate(
    lines: list[PricingLineInput], *, margin_rate: Decimal | int | str
) -> CalculatedCandidate:
    """Calculate persisted candidate totals from a quote revision's line inputs."""

    if not lines:
        raise ValueError("At least one quote line is required")
    margin = _exact_decimal(margin_rate)
    calculated_lines = tuple(
        calculate_candidate_line(
            quantity=line.quantity,
            material_cost=line.material_cost,
            labor_cost=line.labor_cost,
            overhead_cost=line.overhead_cost,
            margin_rate=margin,
        )
        for line in lines
    )
    total_cost_raw = sum((line.total_cost_raw for line in calculated_lines), Decimal("0"))
    total_price_raw = sum((line.total_price_raw for line in calculated_lines), Decimal("0"))
    gross_profit_raw = total_price_raw - total_cost_raw
    margin_rate_raw = gross_profit_raw / total_price_raw if total_price_raw > 0 else Decimal("0")
    total_quantity = sum(line.quantity for line in calculated_lines)
    average_unit_price_raw = total_price_raw / total_quantity
    return CalculatedCandidate(
        lines=calculated_lines,
        total_cost_raw=total_cost_raw,
        total_price_raw=total_price_raw,
        gross_profit_raw=gross_profit_raw,
        margin_rate_raw=margin_rate_raw,
        total_cost=quantize_money(total_cost_raw),
        total_price=quantize_money(total_price_raw),
        gross_profit=quantize_money(gross_profit_raw),
        margin_rate=quantize_rate(margin_rate_raw),
        average_unit_price_raw=average_unit_price_raw,
    )


def validate_candidate(
    candidate: CalculatedCandidate,
    *,
    minimum_margin_rate: Decimal | int | str,
    competitor_average_unit_price: Decimal | None,
    competitor_context_included: bool,
) -> CandidateValidation:
    """Apply the V2-05 deterministic validation rules and severity mapping."""

    minimum_margin = _exact_decimal(minimum_margin_rate)
    if minimum_margin < 0 or minimum_margin >= 1:
        raise ValueError("Minimum margin rate must be greater than or equal to 0 and less than 1")

    price_above_cost = candidate.total_price_raw > candidate.total_cost_raw
    # Margin is persisted and governed at the V2 NUMERIC(9,6) contract boundary.
    # Comparing that canonical value avoids a repeating-decimal artifact at an exact threshold.
    canonical_minimum_margin = quantize_rate(minimum_margin)
    minimum_margin_passed = candidate.margin_rate >= canonical_minimum_margin
    checks: list[ValidationCheckCalculation] = [
        ValidationCheckCalculation(
            code="price_above_cost",
            severity=ValidationSeverity.ERROR,
            passed=price_above_cost,
            message="Candidate price must be greater than total cost.",
            details={
                "candidate_total_price": decimal_string(candidate.total_price),
                "candidate_total_cost": decimal_string(candidate.total_cost),
            },
        ),
        ValidationCheckCalculation(
            code="minimum_margin",
            severity=ValidationSeverity.ERROR,
            passed=minimum_margin_passed,
            message="Candidate margin must meet the active cost profile minimum.",
            details={
                "candidate_margin_rate": decimal_string(candidate.margin_rate, rate=True),
                "minimum_margin_rate": decimal_string(canonical_minimum_margin, rate=True),
            },
        ),
    ]

    if competitor_context_included and competitor_average_unit_price is not None:
        market_floor = competitor_average_unit_price * Decimal("0.80")
        market_ceiling = competitor_average_unit_price * Decimal("1.50")
        checks.extend(
            [
                ValidationCheckCalculation(
                    code="market_floor",
                    severity=ValidationSeverity.WARNING,
                    passed=candidate.average_unit_price_raw >= market_floor,
                    message="Candidate average unit price should not be more than 20 percent below market context.",
                    details={
                        "candidate_average_unit_price": decimal_string(candidate.average_unit_price_raw),
                        "market_average_unit_price": decimal_string(competitor_average_unit_price),
                        "market_floor": decimal_string(market_floor),
                    },
                ),
                ValidationCheckCalculation(
                    code="market_ceiling",
                    severity=ValidationSeverity.WARNING,
                    passed=candidate.average_unit_price_raw <= market_ceiling,
                    message="Candidate average unit price should not be more than 50 percent above market context.",
                    details={
                        "candidate_average_unit_price": decimal_string(candidate.average_unit_price_raw),
                        "market_average_unit_price": decimal_string(competitor_average_unit_price),
                        "market_ceiling": decimal_string(market_ceiling),
                    },
                ),
            ]
        )
    else:
        checks.extend(
            [
                ValidationCheckCalculation(
                    code="market_floor",
                    severity=ValidationSeverity.WARNING,
                    passed=True,
                    message="Market floor was not evaluated because competitor context was not available.",
                    details={"evaluated": False},
                ),
                ValidationCheckCalculation(
                    code="market_ceiling",
                    severity=ValidationSeverity.WARNING,
                    passed=True,
                    message="Market ceiling was not evaluated because competitor context was not available.",
                    details={"evaluated": False},
                ),
            ]
        )

    if any(not check.passed and check.severity is ValidationSeverity.ERROR for check in checks):
        return CandidateValidation(ValidationStatus.FAILED, RiskLevel.HIGH, tuple(checks))
    if any(not check.passed and check.severity is ValidationSeverity.WARNING for check in checks):
        return CandidateValidation(ValidationStatus.WARNING, RiskLevel.MEDIUM, tuple(checks))
    return CandidateValidation(ValidationStatus.PASSED, RiskLevel.LOW, tuple(checks))
