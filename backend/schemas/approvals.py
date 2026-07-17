"""Public, role-safe request and response contracts for V2 approvals."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from backend.domain.approvals import ApprovalStatus
from backend.domain.pricing import RiskLevel, ValidationStatus
from backend.domain.quotes import QuoteStatus


class _ApprovalText(BaseModel):
    @field_validator("reason", mode="before", check_fields=False)
    @classmethod
    def normalize_reason(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class ApprovalRequestCreate(_ApprovalText):
    quote_id: int = Field(gt=0)
    pricing_check_id: int = Field(gt=0)
    price_candidate_id: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=2000)


class ApprovalDecisionRequest(_ApprovalText):
    version: int = Field(gt=0)
    reason: str | None = Field(default=None, max_length=2000)


class ApprovalDecisionResponse(BaseModel):
    id: int
    decision: ApprovalStatus
    reviewer_user_id: int
    reason: str | None
    result_quote_revision_id: int
    demo_self_approval_used: bool
    created_at: datetime


class ApprovalRequestResponse(BaseModel):
    id: int
    quote_id: int
    quote_revision_id: int
    quote_version: int
    pricing_check_id: int
    price_candidate_id: int
    requester_user_id: int
    status: ApprovalStatus
    quote_current_status: QuoteStatus
    validation_status: ValidationStatus
    risk_level: RiskLevel
    currency: str
    candidate_total_price: str
    candidate_gross_profit: str
    candidate_margin_rate: str
    request_reason: str | None
    version: int
    created_at: datetime
    updated_at: datetime
    decision: ApprovalDecisionResponse | None


class ApprovalRequestPageResponse(BaseModel):
    items: list[ApprovalRequestResponse]
    page: int
    page_size: int
    total: int
