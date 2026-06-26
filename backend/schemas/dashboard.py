from pydantic import BaseModel


class DashboardChartPoint(BaseModel):
    name: str
    value: int


class PricingDashboardKpis(BaseModel):
    total_products: int
    active_products: int
    total_competitors: int
    total_competitor_prices: int
    total_cost_profiles: int
    total_price_tables: int
    active_price_tables: int
    draft_price_tables: int
    archived_price_tables: int


class CandidateDashboardKpis(BaseModel):
    total_candidate_tables: int
    generated_candidate_tables: int
    approved_candidate_tables: int
    rejected_candidate_tables: int


class ValidationDashboardKpis(BaseModel):
    pass_count: int
    warning_count: int
    fail_count: int
    high_risk_count: int


class QuoteRequestDashboardKpis(BaseModel):
    submitted: int
    reviewing: int
    quoted: int
    rejected: int
    archived: int


class ApprovalDashboardKpis(BaseModel):
    total_approvals: int
    recent_approvals_count: int


class OperationsDashboardKpis(BaseModel):
    total_audit_logs: int
    recent_audit_logs_count: int
    total_csv_imports: int | None = None
    failed_csv_imports: int | None = None
    total_workflow_jobs: int
    completed_workflow_jobs: int
    failed_workflow_jobs: int


class DashboardCharts(BaseModel):
    price_table_status: list[DashboardChartPoint]
    candidate_status: list[DashboardChartPoint]
    validation_status: list[DashboardChartPoint]
    quote_request_status: list[DashboardChartPoint]
    workflow_job_status: list[DashboardChartPoint]


class DashboardKpisResponse(BaseModel):
    generated_at: str
    recent_window_days: int
    pricing: PricingDashboardKpis
    candidates: CandidateDashboardKpis
    validation: ValidationDashboardKpis
    quote_requests: QuoteRequestDashboardKpis
    approvals: ApprovalDashboardKpis
    operations: OperationsDashboardKpis
    charts: DashboardCharts
    notes: list[str]


class DashboardAttentionItem(BaseModel):
    severity: str
    title: str
    message: str
    related_area: str
    count: int | None = None
    route: str | None = None


class DashboardApprovalQueue(BaseModel):
    pending_candidate_tables: int
    recently_approved_candidate_tables: int
    recently_rejected_candidate_tables: int
    active_price_tables: int
    draft_price_tables: int
    human_approval_required: bool
    automatic_activation_enabled: bool


class DashboardValidationSummary(BaseModel):
    pass_count: int
    warning_count: int
    fail_count: int
    high_risk_count: int
    latest_validation_at: str | None = None


class DashboardDataQualitySection(BaseModel):
    exists: bool
    count: int
    status: str


class DashboardDataQuality(BaseModel):
    products: DashboardDataQualitySection
    competitors: DashboardDataQualitySection
    competitor_prices: DashboardDataQualitySection
    cost_profiles: DashboardDataQualitySection
    price_tables: DashboardDataQualitySection
    candidate_tables: DashboardDataQualitySection
    ready_for_pricing_workflow: bool


class DashboardQuoteRequestSummary(BaseModel):
    total: int
    pending: int
    reviewing: int
    quoted: int
    rejected: int
    archived: int
    recent_count: int


class DashboardJobHealth(BaseModel):
    total: int
    queued: int
    running: int
    completed: int
    failed: int
    cancelled: int
    latest_failed_job_id: int | None = None
    latest_failed_job_title: str | None = None
    latest_failed_at: str | None = None


class DashboardAuditEvent(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: int | None = None
    actor_name: str | None = None
    actor_role: str | None = None
    created_at: str


class DashboardAuditActivity(BaseModel):
    recent_audit_log_count: int
    recent_blocked_permission_count: int
    recent_approval_event_count: int
    latest_events: list[DashboardAuditEvent]


class DashboardSystemReadiness(BaseModel):
    backend_health_available: bool
    database_status_available: bool
    openai_configured: bool
    fallback_mode_available: bool
    audit_logging_available: bool
    job_system_available: bool
    database_type: str


class DashboardInsightsResponse(BaseModel):
    generated_at: str
    recent_window_days: int
    attention_items: list[DashboardAttentionItem]
    approval_queue: DashboardApprovalQueue
    validation_summary: DashboardValidationSummary
    data_quality: DashboardDataQuality
    quote_request_summary: DashboardQuoteRequestSummary
    job_health: DashboardJobHealth
    audit_activity: DashboardAuditActivity
    system_readiness: DashboardSystemReadiness
    notes: list[str]
