from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from backend.domain.customer_requests import ProductCode
from backend.domain.quotes import QuoteStatus


class QuoteTextFields(BaseModel):
    @field_validator("title", "notes", "description", mode="before", check_fields=False)
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value


class QuoteFromRequestCreate(QuoteTextFields):
    request_version: int = Field(gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)


class QuoteDraftUpdate(QuoteTextFields):
    version: int = Field(gt=0)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)
    assignee_user_id: int | None = Field(default=None, gt=0)


class QuoteLineInput(QuoteTextFields):
    description: str = Field(min_length=1, max_length=200)
    product_code: ProductCode
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    options: dict[str, Any] = Field(default_factory=dict)

    @field_validator("unit_price", mode="before")
    @classmethod
    def reject_binary_float_prices(cls, value: object) -> object:
        if isinstance(value, float):
            raise ValueError("Binary float is prohibited for quote money")
        return value


class QuoteLinesReplace(BaseModel):
    version: int = Field(gt=0)
    lines: list[QuoteLineInput] = Field(default_factory=list, max_length=100)


class QuoteLineResponse(BaseModel):
    id: int
    position: int
    description: str
    product_code: ProductCode
    quantity: int
    unit_price: str
    line_total: str
    options: dict[str, Any]


class QuoteRevisionLineResponse(BaseModel):
    id: int
    source_quote_line_id: int | None
    position: int
    description: str
    product_code: ProductCode
    quantity: int
    unit_price: str
    line_total: str
    options: dict[str, Any]


class QuoteRevisionSummaryResponse(BaseModel):
    id: int
    quote_id: int
    revision_number: int
    quote_version: int
    source_request_version: int
    status: QuoteStatus
    total_amount: str
    currency: str
    line_count: int
    formula_version: str
    rounding_policy_version: str
    created_by_user_id: int
    created_at: datetime


class QuoteRevisionDetailResponse(QuoteRevisionSummaryResponse):
    quote_number: str
    title: str
    customer_name: str
    contact_name: str | None
    request_product_code: ProductCode
    request_quantity: int
    notes: str | None
    lines: list[QuoteRevisionLineResponse]


class QuoteListItemResponse(BaseModel):
    id: int
    customer_request_id: int
    quote_number: str
    title: str
    customer_name: str
    request_product_code: ProductCode
    request_quantity: int
    status: QuoteStatus
    currency: str
    total_amount: str
    assignee_user_id: int | None
    created_by_user_id: int
    version: int
    current_revision_number: int
    updated_at: datetime


class QuoteDetailResponse(QuoteListItemResponse):
    contact_name: str | None
    source_request_version: int
    formula_version: str
    rounding_policy_version: str
    notes: str | None
    created_at: datetime
    lines: list[QuoteLineResponse]
    current_revision: QuoteRevisionSummaryResponse


class QuotePageResponse(BaseModel):
    items: list[QuoteListItemResponse]
    page: int
    page_size: int
    total: int


class QuoteRevisionPageResponse(BaseModel):
    items: list[QuoteRevisionSummaryResponse]
    page: int
    page_size: int
    total: int
