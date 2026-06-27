from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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


class UserResponse(OrmModel):
    id: int
    username: str
    display_name: str
    role: Literal["admin", "manager", "viewer"]
    active: bool = True


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class DemoUserResponse(BaseModel):
    username: str
    display_name: str
    role: Literal["admin", "manager", "viewer"]
    demo_only: bool = True
    password_hint: str


class AuditLogResponse(OrmModel):
    id: int
    actor_user_id: int | None = None
    actor_username: str
    actor_role: str
    action: str
    entity_type: str
    entity_id: str | None = None
    summary: str
    metadata_json: str
    created_at: datetime


class DashboardActionCount(BaseModel):
    action: str
    count: int


class DashboardLatestAction(BaseModel):
    action: str
    actor_username: str
    created_at: datetime


class DashboardQuoteMetrics(BaseModel):
    total_quote_requests: int
    new_quote_requests: int
    reviewing_quote_requests: int
    quoted_quote_requests: int
    closed_quote_requests: int
    cancelled_quote_requests: int


class DashboardApprovalMetrics(BaseModel):
    total_approval_requests: int
    pending_approval_requests: int
    approved_requests: int
    rejected_requests: int
    approval_rate: float
    rejection_rate: float
    average_estimated_margin_rate: float | None = None


class DashboardValidationMetrics(BaseModel):
    passed_validations: int
    warning_validations: int
    failed_validations: int
    low_risk_count: int
    medium_risk_count: int
    high_risk_count: int


class DashboardPricingMetrics(BaseModel):
    total_products: int
    active_products: int
    total_price_tables: int
    draft_price_tables: int
    active_price_tables: int
    archived_price_tables: int
    total_cost_profiles: int
    average_target_margin_rate: float | None = None
    average_approved_margin_rate: float | None = None


class DashboardWorkflowMetrics(BaseModel):
    total_workflow_jobs: int
    pending_jobs: int
    running_jobs: int
    completed_jobs: int
    failed_jobs: int
    cancelled_jobs: int
    job_success_rate: float


class DashboardAuditMetrics(BaseModel):
    total_audit_logs: int
    recent_audit_log_count: int
    top_actions: list[DashboardActionCount]
    latest_actions: list[DashboardLatestAction]


class DashboardSummaryMetrics(BaseModel):
    total_products: int
    total_quote_requests: int
    total_approval_requests: int
    approved_requests: int
    rejected_requests: int
    pending_approval_requests: int
    average_estimated_margin_rate: float | None = None
    high_risk_count: int
    completed_jobs: int
    failed_jobs: int


class DashboardResponse(BaseModel):
    generated_at: datetime
    summary: DashboardSummaryMetrics
    quote_metrics: DashboardQuoteMetrics
    approval_metrics: DashboardApprovalMetrics
    validation_metrics: DashboardValidationMetrics
    pricing_metrics: DashboardPricingMetrics
    workflow_metrics: DashboardWorkflowMetrics
    audit_metrics: DashboardAuditMetrics
    dashboard_notes: list[str]


class CsvImportError(BaseModel):
    row_number: int
    message: str


class CsvImportSummary(BaseModel):
    entity_type: str
    received_rows: int
    created_rows: int
    updated_rows: int
    failed_rows: int
    errors: list[CsvImportError]
    notes: list[str]


class PricingSimulationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=140)
    product_id: int
    quantities: list[int]
    margin_rates: list[float]
    include_competitor_context: bool = False
    notes: str | None = None


class PricingSimulationScenarioResponse(OrmModel):
    id: int
    quantity: int
    margin_rate: float
    unit_price: float
    total_price: float
    total_cost: float
    estimated_gross_profit: float
    estimated_margin_rate: float
    validation_status: Literal["passed", "warning", "failed"]
    risk_level: Literal["low", "medium", "high"]
    created_at: datetime


class PricingSimulationResponse(OrmModel):
    id: int
    name: str
    product_id: int
    product_name: str
    unit_cost: float
    include_competitor_context: bool
    scenario_count: int
    scenarios: list[PricingSimulationScenarioResponse]
    competitor_context: CompetitorContextResponse | None = None
    notes: str | None = None
    created_by_username: str
    created_at: datetime
    simulation_notes: list[str]


RiskPreference = Literal["conservative", "balanced", "aggressive"]


class StrategyTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=140)
    strategy_code: str = Field(..., min_length=1, max_length=80)
    description: str | None = None
    margin_rates: list[float]
    default_quantities: list[int] = Field(default_factory=lambda: [1, 10, 50])
    include_competitor_context_default: bool = False
    risk_preference: RiskPreference = "balanced"
    active: bool = True
    notes: str | None = None

    @field_validator("margin_rates")
    @classmethod
    def validate_margin_rates(cls, value: list[float]) -> list[float]:
        if not value:
            raise ValueError("margin_rates must not be empty")
        if any(margin_rate < 0 or margin_rate >= 1 for margin_rate in value):
            raise ValueError("Each margin rate must be >= 0 and < 1")
        return value

    @field_validator("default_quantities")
    @classmethod
    def validate_default_quantities(cls, value: list[int]) -> list[int]:
        if not value:
            raise ValueError("default_quantities must not be empty")
        if any(quantity <= 0 for quantity in value):
            raise ValueError("Each default quantity must be greater than 0")
        return value


class StrategyTemplateCreate(StrategyTemplateBase):
    pass


class StrategyTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=140)
    strategy_code: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    margin_rates: list[float] | None = None
    default_quantities: list[int] | None = None
    include_competitor_context_default: bool | None = None
    risk_preference: RiskPreference | None = None
    active: bool | None = None
    notes: str | None = None

    @field_validator("margin_rates")
    @classmethod
    def validate_optional_margin_rates(cls, value: list[float] | None) -> list[float] | None:
        if value is None:
            return value
        return StrategyTemplateBase.validate_margin_rates(value)

    @field_validator("default_quantities")
    @classmethod
    def validate_optional_quantities(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value
        return StrategyTemplateBase.validate_default_quantities(value)


class StrategyTemplateResponse(BaseModel):
    id: int
    name: str
    strategy_code: str
    description: str | None = None
    margin_rates: list[float]
    default_quantities: list[int]
    include_competitor_context_default: bool
    risk_preference: RiskPreference
    active: bool
    notes: str | None = None
    created_by_username: str
    created_at: datetime
    updated_at: datetime


class StrategyTemplateCandidatePriceRequest(BaseModel):
    product_id: int
    quantity: int
    include_competitor_context: bool | None = None


class StrategyTemplatePricingSimulationRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=140)
    product_id: int
    quantities: list[int] | None = None
    include_competitor_context: bool | None = None
    notes: str | None = None

    @field_validator("quantities")
    @classmethod
    def validate_optional_quantities(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return value
        return StrategyTemplateBase.validate_default_quantities(value)


QuoteRequestStatus = Literal["new", "reviewing", "quoted", "closed", "cancelled"]


class CustomerQuoteRequestCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=120)
    customer_email: str = Field(..., min_length=1, max_length=160)
    customer_company: str | None = None
    product_id: int
    quantity: int
    requested_due_date: datetime | None = None
    request_note: str | None = None


class CustomerQuoteRequestUpdate(BaseModel):
    customer_name: str | None = Field(default=None, min_length=1, max_length=120)
    customer_email: str | None = Field(default=None, min_length=1, max_length=160)
    customer_company: str | None = None
    quantity: int | None = None
    requested_due_date: datetime | None = None
    request_note: str | None = None
    assigned_to_username: str | None = None
    internal_note: str | None = None


class CustomerQuoteRequestStatusUpdate(BaseModel):
    status: QuoteRequestStatus
    assigned_to_username: str | None = None
    internal_note: str | None = None


class CustomerQuoteCandidatePriceRequest(BaseModel):
    margin_rates: list[float] | None = None
    include_competitor_context: bool = False


class CustomerQuoteRequestResponse(OrmModel):
    id: int
    customer_name: str
    customer_email: str
    customer_company: str | None = None
    product_id: int
    product_name: str
    quantity: int
    requested_due_date: datetime | None = None
    request_note: str | None = None
    status: QuoteRequestStatus
    assigned_to_username: str | None = None
    internal_note: str | None = None
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime | None = None
    workflow_notes: list[str]


class PriceTableSummaryResponse(BaseModel):
    price_table_id: int
    name: str
    status: str
    item_count: int
    average_price: float | None = None
    min_price: float | None = None
    max_price: float | None = None
    average_margin_rate: float | None = None
    created_at: datetime
    updated_at: datetime


class PriceTableSnapshotCreate(BaseModel):
    label: str = Field(..., min_length=1, max_length=140)
    note: str | None = None


class PriceTableSnapshotItemResponse(OrmModel):
    id: int
    snapshot_id: int
    product_id: int
    product_name: str
    product_sku: str
    price: float
    margin_rate: float
    created_at: datetime


class PriceTableSnapshotResponse(OrmModel):
    id: int
    price_table_id: int
    label: str
    note: str | None = None
    created_by_username: str
    created_at: datetime
    item_count: int
    items: list[PriceTableSnapshotItemResponse]


class PriceTableCompareRequest(BaseModel):
    base_price_table_id: int
    target_price_table_id: int


class PriceTableSnapshotCompareRequest(BaseModel):
    base_snapshot_id: int
    target_snapshot_id: int


class PriceTableComparisonSummary(BaseModel):
    added_items: int
    removed_items: int
    changed_items: int
    unchanged_items: int
    average_price_delta: float | None = None
    average_price_delta_rate: float | None = None


class PriceTableComparisonChange(BaseModel):
    product_id: int
    product_name: str
    product_sku: str
    change_type: Literal["added", "removed", "changed", "unchanged"]
    base_price: float | None = None
    target_price: float | None = None
    price_delta: float | None = None
    price_delta_rate: float | None = None
    base_margin_rate: float | None = None
    target_margin_rate: float | None = None
    margin_delta: float | None = None


class PriceTableComparisonResponse(BaseModel):
    base_id: int
    target_id: int
    base_name: str
    target_name: str
    summary: PriceTableComparisonSummary
    changes: list[PriceTableComparisonChange]
    comparison_notes: list[str]


WorkflowJobStatus = Literal["pending", "running", "completed", "failed", "cancelled"]
WorkflowJobType = Literal["pricing_simulation", "price_validation_batch", "quote_request_review"]


class WorkflowJobCreate(BaseModel):
    job_type: WorkflowJobType
    title: str = Field(..., min_length=1, max_length=140)
    description: str | None = None
    input: dict = Field(default_factory=dict)


class WorkflowJobResponse(OrmModel):
    id: int
    job_type: WorkflowJobType
    status: WorkflowJobStatus
    title: str
    description: str | None = None
    input: dict
    result: dict | None = None
    error_message: str | None = None
    created_by_username: str
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    workflow_notes: list[str]


class ScenarioComparisonScenarioInput(BaseModel):
    label: str | None = Field(default=None, max_length=120)
    quantity: int
    margin_rate: float


class ScenarioComparisonCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=140)
    description: str | None = None
    product_id: int
    scenarios: list[ScenarioComparisonScenarioInput]
    include_competitor_context: bool = False


class ScenarioComparisonSummary(BaseModel):
    highest_margin_label: str | None = None
    highest_profit_label: str | None = None
    lowest_risk_label: str | None = None
    lowest_unit_price_label: str | None = None
    highest_unit_price_label: str | None = None
    highest_total_price_label: str | None = None
    unit_price_range: float
    gross_profit_range: float
    risk_distribution: dict[str, int]


class ScenarioComparisonItemResponse(OrmModel):
    id: int
    comparison_id: int
    label: str
    source_type: str
    source_id: str | None = None
    quantity: int
    margin_rate: float
    unit_cost: float
    unit_price: float
    total_cost: float
    total_price: float
    estimated_gross_profit: float
    estimated_margin_rate: float
    validation_status: Literal["passed", "warning", "failed"]
    risk_level: Literal["low", "medium", "high"]
    notes: list[str]
    created_at: datetime


class ScenarioComparisonResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    product_id: int
    product_name: str
    scenario_count: int
    summary: ScenarioComparisonSummary
    scenarios: list[ScenarioComparisonItemResponse]
    competitor_context: CompetitorContextResponse | None = None
    comparison_notes: list[str]
    created_by_username: str
    created_at: datetime
    updated_at: datetime


class HtmlReportCreate(BaseModel):
    report_type: str = Field(..., min_length=1, max_length=40)
    title: str = Field(..., min_length=1, max_length=160)
    source_id: int | None = None


class HtmlReportResponse(OrmModel):
    id: int
    report_type: str
    title: str
    source_type: str
    source_id: str | None = None
    summary_text: str
    created_by_username: str
    created_at: datetime
    updated_at: datetime
    report_notes: list[str]
