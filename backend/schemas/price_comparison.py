from pydantic import BaseModel


class PriceTableComparisonSummary(BaseModel):
    item_count: int
    changed_count: int
    unchanged_count: int
    average_price_delta_rate: float | None
    total_price_delta: float
    warning_count: int


class PriceTableComparisonItem(BaseModel):
    quantity: int
    option_summary: str
    baseline_price: float | None
    comparison_price: float | None
    price_delta: float | None
    price_delta_rate: float | None
    baseline_margin_rate: float | None
    comparison_margin_rate: float | None
    margin_delta: float | None
    change_type: str
    warnings: list[str]


class PriceTableComparisonResponse(BaseModel):
    product_id: int
    product_name: str
    baseline_price_table_id: int | None
    comparison_price_table_id: int
    summary: PriceTableComparisonSummary
    items: list[PriceTableComparisonItem]
    warnings: list[str]


class PriceTableHistoryEntry(BaseModel):
    price_table_id: int
    product_id: int
    product_name: str
    name: str
    status: str
    strategy_name: str
    created_at: str
    updated_at: str
    approval_id: int | None
    approval_action: str | None
    approval_status: str | None
    reviewer_name: str | None
    reviewer_note: str | None
    approved_at: str | None
    candidate_table_id: int | None

