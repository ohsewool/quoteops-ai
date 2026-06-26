from pydantic import BaseModel, Field


class ScenarioRef(BaseModel):
    scenario_type: str = Field(pattern="^(price_table|candidate_table)$")
    scenario_id: int = Field(ge=1)


class ScenarioComparisonRequest(BaseModel):
    base: ScenarioRef
    compare: ScenarioRef


class ScenarioSummary(BaseModel):
    scenario_type: str
    scenario_id: int
    product_id: int
    product_name: str
    name: str
    status: str
    strategy_name: str
    item_count: int
    latest_updated_at: str
    validation: dict | None = None
    approval_readiness: dict


class ScenarioComparisonSummary(BaseModel):
    total_compared_items: int
    matching_item_count: int
    missing_item_count: int
    average_price_difference: float | None
    min_price_difference: float | None
    max_price_difference: float | None
    average_price_difference_rate: float | None
    average_margin_difference: float | None
    price_increase_count: int
    price_decrease_count: int
    unchanged_count: int
    warning_count: int


class ScenarioItemDifference(BaseModel):
    quantity: int
    option_summary: str
    match_status: str
    base_price: float | None
    compare_price: float | None
    price_difference: float | None
    price_difference_rate: float | None
    base_margin_rate: float | None
    compare_margin_rate: float | None
    margin_difference: float | None
    base_validation_status: str | None = None
    compare_validation_status: str | None = None
    warnings: list[str]


class ScenarioValidationComparison(BaseModel):
    base: dict | None
    compare: dict | None
    notes: list[str]


class ScenarioApprovalReadinessComparison(BaseModel):
    base: dict
    compare: dict
    notes: list[str]


class ScenarioComparisonResponse(BaseModel):
    base: ScenarioSummary
    compare: ScenarioSummary
    summary: ScenarioComparisonSummary
    item_differences: list[ScenarioItemDifference]
    validation_comparison: ScenarioValidationComparison
    approval_readiness: ScenarioApprovalReadinessComparison
    warnings: list[str]
    notes: list[str]
