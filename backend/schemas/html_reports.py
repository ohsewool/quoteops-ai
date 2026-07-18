"""Role-safe contracts for immutable approved-Quote HTML report artifacts."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.domain.pricing import RiskLevel, ValidationStatus
from backend.domain.quotes import QuoteStatus


class HtmlReportCreate(BaseModel):
    approval_request_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    report_type: Literal["approved_quote"] = "approved_quote"
    predecessor_report_id: int | None = Field(default=None, gt=0)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("title must not be blank")
        return normalized


class HtmlReportLineResponse(BaseModel):
    position: int
    description: str
    product_code: str
    quantity: int
    unit_price: str
    total_price: str


class HtmlReportHistoryEntry(BaseModel):
    id: int
    title: str
    predecessor_report_id: int | None
    created_by_user_id: int
    created_at: datetime


class HtmlReportResponse(BaseModel):
    id: int
    report_type: Literal["approved_quote"]
    title: str
    quote_id: int
    source_quote_revision_id: int
    source_quote_revision_number: int
    source_quote_status: QuoteStatus
    source_quote_number: str
    approval_request_id: int
    approval_decision_id: int
    predecessor_report_id: int | None
    created_by_user_id: int
    currency: str
    quote_total_amount: str
    candidate_total_cost: str
    candidate_total_price: str
    candidate_gross_profit: str
    candidate_margin_rate: str
    validation_status: ValidationStatus
    risk_level: RiskLevel
    lines: list[HtmlReportLineResponse]
    summary_text: str
    content_sha256: str
    created_at: datetime
    regeneration_history: list[HtmlReportHistoryEntry]
