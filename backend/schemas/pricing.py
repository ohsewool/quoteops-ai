"""Request and role-safe response contracts for V2 pricing checks."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from backend.domain.customer_requests import ProductCode
from backend.domain.pricing import (
    CompetitorType,
    PricingCheckStatus,
    PricingStrategy,
    ReferencePriceBasis,
    RiskLevel,
    ValidationSeverity,
    ValidationStatus,
)


class _ExactDecimalFields(BaseModel):
    @field_validator(
        "material_cost",
        "labor_cost",
        "overhead_cost",
        "target_margin_rate",
        "reference_price",
        mode="before",
        check_fields=False,
    )
    @classmethod
    def reject_binary_float_values(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Binary float is prohibited for V2 pricing inputs")
        if isinstance(value, str):
            return value.strip()
        return value


class _TextFields(BaseModel):
    @field_validator("name", "description", "notes", "source_note", mode="before", check_fields=False)
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ProductCreate(_TextFields):
    code: ProductCode
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    active: bool = True


class ProductResponse(BaseModel):
    id: int
    code: ProductCode
    name: str
    description: str | None
    active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class ProductPageResponse(BaseModel):
    items: list[ProductResponse]
    page: int
    page_size: int
    total: int


class CostProfileCreate(_ExactDecimalFields):
    product_id: int = Field(gt=0)
    material_cost: Decimal = Field(ge=0)
    labor_cost: Decimal = Field(ge=0)
    overhead_cost: Decimal = Field(ge=0)
    target_margin_rate: Decimal = Field(ge=0, lt=1)
    active: bool = True


class CostProfileResponse(BaseModel):
    """Manager/admin-only source-data response. Never used for Viewer pricing reads."""

    id: int
    product_id: int
    material_cost: str
    labor_cost: str
    overhead_cost: str
    target_margin_rate: str
    active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class CostProfilePageResponse(BaseModel):
    items: list[CostProfileResponse]
    page: int
    page_size: int
    total: int


class CompetitorCreate(_TextFields):
    name: str = Field(min_length=1, max_length=120)
    competitor_type: CompetitorType
    notes: str | None = Field(default=None, max_length=2000)
    active: bool = True


class CompetitorResponse(BaseModel):
    id: int
    name: str
    competitor_type: CompetitorType
    notes: str | None
    active: bool
    version: int
    created_at: datetime
    updated_at: datetime


class CompetitorPageResponse(BaseModel):
    items: list[CompetitorResponse]
    page: int
    page_size: int
    total: int


class CompetitorReferenceCreate(_ExactDecimalFields, _TextFields):
    competitor_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    price_basis: ReferencePriceBasis
    reference_price: Decimal = Field(ge=0)
    source_note: str | None = Field(default=None, max_length=2000)
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def require_timezone_aware_observation(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone offset")
        return value


class CompetitorReferenceResponse(BaseModel):
    id: int
    competitor_id: int
    product_id: int
    quantity: int
    price_basis: ReferencePriceBasis
    reference_price: str
    source_note: str | None
    observed_at: datetime
    created_at: datetime


class CompetitorReferencePageResponse(BaseModel):
    items: list[CompetitorReferenceResponse]
    page: int
    page_size: int
    total: int


class PricingCheckCreate(BaseModel):
    quote_version: int = Field(gt=0)
    quote_revision_id: int = Field(gt=0)
    selected_strategy: PricingStrategy = PricingStrategy.TARGET_MARGIN
    include_competitor_context: bool = True


class PricingValidationCheckResponse(BaseModel):
    code: str
    severity: ValidationSeverity
    passed: bool
    message: str


class PricingValidationResponse(BaseModel):
    status: ValidationStatus
    risk_level: RiskLevel
    minimum_margin_rate: str
    checks: list[PricingValidationCheckResponse]


class PriceCandidateLineResponse(BaseModel):
    """Viewer-safe candidate output: generated prices only, no cost components."""

    id: int
    position: int
    product_code: ProductCode
    quantity: int
    unit_price: str
    total_price: str


class PriceCandidateResponse(BaseModel):
    id: int
    position: int
    strategy: PricingStrategy
    margin_rate: str
    is_selected: bool
    total_cost: str
    total_price: str
    estimated_gross_profit: str
    estimated_margin_rate: str
    notes: list[str]
    validation: PricingValidationResponse
    lines: list[PriceCandidateLineResponse]


class CompetitorContextSummaryResponse(BaseModel):
    included: bool
    reference_count: int
    average_unit_price: str | None
    source_version: str
    earliest_observed_at: datetime | None
    latest_observed_at: datetime | None


class PricingCheckSummaryResponse(BaseModel):
    id: int
    quote_id: int
    quote_revision_id: int
    quote_version: int
    status: PricingCheckStatus
    selected_strategy: PricingStrategy
    selected_candidate_id: int
    selected_total_price: str
    selected_gross_profit: str
    selected_margin_rate: str
    minimum_margin_rate: str
    candidate_count: int
    validation_status: ValidationStatus
    risk_level: RiskLevel
    currency: str
    formula_version: str
    validation_rule_version: str
    rounding_policy_version: str
    created_by_user_id: int
    created_at: datetime


class PricingCheckDetailResponse(PricingCheckSummaryResponse):
    total_cost: str
    competitor_context: CompetitorContextSummaryResponse
    candidates: list[PriceCandidateResponse]


class PricingCheckPageResponse(BaseModel):
    items: list[PricingCheckSummaryResponse]
    page: int
    page_size: int
    total: int
