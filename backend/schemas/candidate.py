from pydantic import BaseModel, Field, model_validator


class CandidateGenerateRequest(BaseModel):
    product_id: int | None = Field(default=None, ge=1)
    product_slug: str | None = Field(default=None, min_length=1)
    option_summary: str = Field(min_length=1)
    quantities: list[int] = Field(min_length=1)
    strategy_name: str | None = Field(default=None, min_length=1)
    strategy_template_id: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def require_product_identifier(self):
        if self.product_id is None and not self.product_slug:
            raise ValueError("Either product_id or product_slug is required.")
        if self.strategy_template_id is None and not self.strategy_name:
            raise ValueError("Either strategy_name or strategy_template_id is required.")
        return self


class CandidateStrategyTemplateInfo(BaseModel):
    id: int
    name: str
    slug: str
    strategy_name: str
    market_position: str
    margin_bias: str
    competitor_weight_mode: str
    rounding_unit: int


class CandidateMarketSummary(BaseModel):
    lowest_price: float | None
    highest_price: float | None
    average_price: float | None
    median_price: float | None
    count: int


class CandidatePriceItem(BaseModel):
    quantity: int
    option_summary: str
    candidate_price: float
    unit_price: float
    cost_floor_price: float
    estimated_margin_rate: float
    market_lowest_price: float | None
    market_average_price: float | None
    market_median_price: float | None
    market_highest_price: float | None
    market_summary: CandidateMarketSummary
    decision_reason_codes: list[str]
    warnings: list[str]


class CandidateGenerationSummary(BaseModel):
    lowest_candidate_price: float | None
    highest_candidate_price: float | None
    average_candidate_price: float | None
    total_market_references: int
    item_count: int


class CandidateGenerateResponse(BaseModel):
    pricing_session_id: int
    candidate_table_id: int
    candidate_table_name: str
    product_id: int
    product_name: str
    option_summary: str
    strategy_name: str
    status: str
    rounding_rule: str
    strategy_template: CandidateStrategyTemplateInfo | None = None
    items: list[CandidatePriceItem]
    summary: CandidateGenerationSummary
    warnings: list[str]
