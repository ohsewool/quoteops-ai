"""Deterministic pricing vocabulary shared by the V2 pricing-check domain."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum


class CompetitorType(StrEnum):
    LOCAL_SHOP = "local_shop"
    SIMILAR_SIZE = "similar_size"
    PREMIUM_SHOP = "premium_shop"
    LARGE_ONLINE = "large_online"
    ULTRA_LOW_COST = "ultra_low_cost"
    UNKNOWN = "unknown"


class PricingStrategy(StrEnum):
    LOW_MARGIN = "low_margin"
    TARGET_MARGIN = "target_margin"
    PREMIUM_MARGIN = "premium_margin"


class ReferencePriceBasis(StrEnum):
    UNIT_PRICE = "unit_price"
    TOTAL_PRICE = "total_price"


class PricingCheckStatus(StrEnum):
    READY = "ready"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


class ValidationStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"


DEFAULT_MARGIN_RATES = (Decimal("0.250000"), Decimal("0.350000"), Decimal("0.450000"))
DEFAULT_STRATEGIES = (
    PricingStrategy.LOW_MARGIN,
    PricingStrategy.TARGET_MARGIN,
    PricingStrategy.PREMIUM_MARGIN,
)
CANDIDATE_FORMULA_VERSION = "quote-cost-margin-v1"
VALIDATION_RULE_VERSION = "pricing-validation-v1"
COMPETITOR_CONTEXT_VERSION = "competitor-reference-v1"
PRICING_ROUNDING_POLICY_VERSION = "krw-half-up-v1"
