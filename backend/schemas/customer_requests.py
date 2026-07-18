from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.domain.customer_requests import CustomerRequestStatus, ProductCode


class RequestTextFields(BaseModel):
    @field_validator("customer_name", "contact_name", "notes", mode="before", check_fields=False)
    @classmethod
    def strip_text(cls, value: object) -> object:
        if value is None:
            return value
        if not isinstance(value, str):
            return value
        return value.strip()


class CustomerRequestCreate(RequestTextFields):
    customer_name: str = Field(min_length=1, max_length=160)
    contact_name: str | None = Field(default=None, max_length=128)
    product_code: ProductCode
    quantity: int = Field(gt=0)
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    assignee_user_id: int | None = Field(default=None, gt=0)


class CustomerRequestUpdate(RequestTextFields):
    version: int = Field(gt=0)
    customer_name: str | None = Field(default=None, min_length=1, max_length=160)
    contact_name: str | None = Field(default=None, max_length=128)
    product_code: ProductCode | None = None
    quantity: int | None = Field(default=None, gt=0)
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    assignee_user_id: int | None = Field(default=None, gt=0)


class CustomerRequestTransition(BaseModel):
    version: int = Field(gt=0)
    target_status: CustomerRequestStatus


class CustomerRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_name: str
    contact_name: str | None
    product_code: ProductCode
    quantity: int
    due_date: date | None
    notes: str | None
    status: CustomerRequestStatus
    assignee_user_id: int | None
    created_by_user_id: int
    version: int
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    ready_for_quote_conversion: bool
    allowed_transitions: list[CustomerRequestStatus]


class CustomerRequestPageResponse(BaseModel):
    items: list[CustomerRequestResponse]
    page: int
    page_size: int
    total: int


class CustomerRequestAuditEventResponse(BaseModel):
    id: int
    action: str
    actor_user_id: int
    actor_username: str
    request_id: str
    metadata: dict[str, object]
    created_at: datetime


class CustomerRequestAuditPageResponse(BaseModel):
    items: list[CustomerRequestAuditEventResponse]
