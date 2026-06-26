from pydantic import BaseModel, Field, model_validator


class VolumeAssumption(BaseModel):
    quantity: int = Field(ge=1)
    expected_order_count: int = Field(ge=0)


class PricingSimulationRequest(BaseModel):
    product_id: int | None = Field(default=None, ge=1)
    product_slug: str | None = Field(default=None, min_length=1)
    candidate_table_id: int = Field(ge=1)
    baseline_price_table_id: int | None = Field(default=None, ge=1)
    option_summary: str | None = Field(default=None, min_length=1)
    volume_assumptions: list[VolumeAssumption] | None = None

    @model_validator(mode="after")
    def require_product_identifier(self):
        if self.product_id is None and not self.product_slug:
            raise ValueError("Either product_id or product_slug is required.")
        return self


class PricingSimulationSummary(BaseModel):
    item_count: int
    baseline_total_revenue: float
    candidate_total_revenue: float
    revenue_delta: float
    baseline_total_gross_profit: float
    candidate_total_gross_profit: float
    gross_profit_delta: float
    average_margin_delta: float | None
    warning_count: int


class PricingSimulationItem(BaseModel):
    quantity: int
    option_summary: str
    expected_order_count: int
    baseline_price: float | None
    candidate_price: float
    price_delta: float | None
    price_delta_rate: float | None
    base_cost: float | None
    baseline_margin_rate: float | None
    candidate_margin_rate: float | None
    margin_delta: float | None
    baseline_revenue: float | None
    candidate_revenue: float
    revenue_delta: float | None
    baseline_gross_profit: float | None
    candidate_gross_profit: float | None
    gross_profit_delta: float | None
    market_lowest_price: float | None
    market_average_price: float | None
    market_highest_price: float | None
    candidate_vs_market_average_rate: float | None
    warnings: list[str]


class PricingSimulationResponse(BaseModel):
    product_id: int
    product_name: str
    candidate_table_id: int
    baseline_price_table_id: int | None
    summary: PricingSimulationSummary
    items: list[PricingSimulationItem]
    warnings: list[str]
