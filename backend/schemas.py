from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str


class SystemStatusResponse(BaseModel):
    service: str
    database_configured: bool
    database_type: str
    openai_configured: bool
    demo_tools_enabled: bool


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    sku: str = Field(..., min_length=1, max_length=80)
    category: str = Field(..., min_length=1, max_length=80)
    description: str | None = None
    active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    sku: str | None = Field(default=None, min_length=1, max_length=80)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    active: bool | None = None


class ProductResponse(ProductBase, OrmModel):
    id: int
    created_at: datetime
    updated_at: datetime


class CompetitorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    channel: str = Field(..., min_length=1, max_length=80)
    notes: str | None = None
    active: bool = True


class CompetitorCreate(CompetitorBase):
    pass


class CompetitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    channel: str | None = Field(default=None, min_length=1, max_length=80)
    notes: str | None = None
    active: bool | None = None


class CompetitorResponse(CompetitorBase, OrmModel):
    id: int
    created_at: datetime
    updated_at: datetime


class CompetitorPriceCreate(BaseModel):
    competitor_id: int
    product_id: int
    reference_price: float = Field(..., gt=0)
    source_note: str | None = None
    observed_at: datetime | None = None


class CompetitorPriceResponse(OrmModel):
    id: int
    competitor_id: int
    product_id: int
    reference_price: float
    source_note: str | None
    observed_at: datetime
    created_at: datetime


class CostProfileBase(BaseModel):
    product_id: int
    material_cost: float = Field(..., ge=0)
    labor_cost: float = Field(..., ge=0)
    overhead_cost: float = Field(..., ge=0)
    target_margin_rate: float = Field(..., ge=0, le=1)
    active: bool = True


class CostProfileCreate(CostProfileBase):
    pass


class CostProfileUpdate(BaseModel):
    product_id: int | None = None
    material_cost: float | None = Field(default=None, ge=0)
    labor_cost: float | None = Field(default=None, ge=0)
    overhead_cost: float | None = Field(default=None, ge=0)
    target_margin_rate: float | None = Field(default=None, ge=0, le=1)
    active: bool | None = None


class CostProfileResponse(CostProfileBase, OrmModel):
    id: int
    created_at: datetime
    updated_at: datetime


PriceTableStatus = Literal["draft", "active", "archived"]


class PriceTableBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=140)
    status: PriceTableStatus = "draft"
    description: str | None = None


class PriceTableCreate(PriceTableBase):
    pass


class PriceTableUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=140)
    status: PriceTableStatus | None = None
    description: str | None = None


class PriceTableResponse(PriceTableBase, OrmModel):
    id: int
    created_at: datetime
    updated_at: datetime


class PriceTableItemCreate(BaseModel):
    product_id: int
    price: float = Field(..., gt=0)
    margin_rate: float = Field(..., ge=0, le=1)


class PriceTableItemResponse(OrmModel):
    id: int
    price_table_id: int
    product_id: int
    price: float
    margin_rate: float
    created_at: datetime


class QuotePreviewRequest(BaseModel):
    product_id: int
    quantity: int
    material_cost: float | None = None
    labor_cost: float | None = None
    overhead_cost: float | None = None
    target_margin_rate: float | None = None


class QuotePreviewResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_cost: float
    total_cost: float
    target_margin_rate: float
    suggested_unit_price: float
    suggested_total_price: float
    estimated_gross_profit: float
    estimated_margin_rate: float
    calculation_notes: list[str]


class CandidatePriceRequest(BaseModel):
    product_id: int
    quantity: int
    margin_rates: list[float] | None = None
    include_competitor_context: bool = False


class CandidatePriceOption(BaseModel):
    strategy: str
    margin_rate: float
    unit_price: float
    total_price: float
    estimated_gross_profit: float
    estimated_margin_rate: float
    notes: list[str]


class CompetitorContextResponse(BaseModel):
    available: bool
    reference_price_count: int
    min_reference_price: float | None = None
    max_reference_price: float | None = None
    average_reference_price: float | None = None


class CandidatePriceResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_cost: float
    total_cost: float
    candidates: list[CandidatePriceOption]
    competitor_context: CompetitorContextResponse | None = None
    calculation_notes: list[str]


class PriceValidationRequest(BaseModel):
    product_id: int
    quantity: int
    candidate_unit_price: float
    minimum_margin_rate: float | None = None
    include_competitor_context: bool = False


class PriceValidationCheck(BaseModel):
    code: str
    severity: Literal["error", "warning"]
    passed: bool
    message: str


class PriceValidationResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    candidate_unit_price: float
    candidate_total_price: float
    unit_cost: float
    total_cost: float
    estimated_gross_profit: float
    estimated_margin_rate: float
    minimum_margin_rate: float
    validation_status: Literal["passed", "warning", "failed"]
    risk_level: Literal["low", "medium", "high"]
    checks: list[PriceValidationCheck]
    competitor_context: CompetitorContextResponse | None = None
    calculation_notes: list[str]


class ApprovalRequestCreate(BaseModel):
    product_id: int
    quantity: int
    proposed_unit_price: float
    minimum_margin_rate: float | None = None
    submitted_note: str | None = None


class ApprovalDecisionRequest(BaseModel):
    reviewer_name: str = Field(..., min_length=1, max_length=120)
    review_note: str | None = None


class ApprovalRequestResponse(OrmModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    proposed_unit_price: float
    proposed_total_price: float
    unit_cost: float
    total_cost: float
    estimated_gross_profit: float
    estimated_margin_rate: float
    minimum_margin_rate: float
    validation_status: Literal["passed", "warning", "failed"]
    risk_level: Literal["low", "medium", "high"]
    status: Literal["pending", "approved", "rejected", "cancelled"]
    submitted_note: str | None = None
    reviewer_name: str | None = None
    review_note: str | None = None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None = None
    workflow_notes: list[str]


class QuoteExplanationRequest(BaseModel):
    product_id: int | None = None
    quantity: int | None = None
    unit_cost: float | None = None
    proposed_unit_price: float | None = None
    candidate_unit_price: float | None = None
    estimated_margin_rate: float | None = None
    validation_status: str | None = None
    risk_level: str | None = None
    approval_request_id: int | None = None
    explanation_audience: str | None = None
    explanation_style: str | None = "concise"


class QuoteExplanationResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_cost: float
    proposed_unit_price: float
    estimated_margin_rate: float
    validation_status: Literal["passed", "warning", "failed"]
    risk_level: Literal["low", "medium", "high"]
    explanation_summary: str
    explanation_bullets: list[str]
    decision_boundaries: list[str]
    explanation_source: str
