from pydantic import BaseModel, Field, field_validator


QUOTE_REQUEST_STATUSES = {"submitted", "reviewing", "quoted", "rejected", "archived"}


class QuoteRequestCreate(BaseModel):
    product_id: int = Field(ge=1)
    requester_name: str = Field(min_length=1)
    requester_email: str = Field(min_length=3)
    requester_phone: str | None = None
    company_name: str | None = None
    quantity: int = Field(ge=1)
    option_summary: str = Field(min_length=1)
    request_note: str | None = None

    @field_validator("requester_name", "requester_email", "option_summary")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Required text fields cannot be blank.")
        return value

    @field_validator("requester_email")
    @classmethod
    def validate_email_shape(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("A valid requester_email is required.")
        return value.lower()

    @field_validator("requester_phone", "company_name", "request_note")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class QuoteRequestUpdate(BaseModel):
    status: str | None = None
    admin_note: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value not in QUOTE_REQUEST_STATUSES:
            raise ValueError("Unsupported quote request status.")
        return value

    @field_validator("admin_note")
    @classmethod
    def normalize_admin_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class QuoteRequest(BaseModel):
    id: int
    product_id: int
    product_name_snapshot: str
    requester_name: str
    requester_email: str
    requester_phone: str | None
    company_name: str | None
    quantity: int
    option_summary: str
    request_note: str | None
    status: str
    quoted_price: float | None
    quoted_unit_price: float | None
    quote_source: str | None
    admin_note: str | None
    created_at: str
    updated_at: str


class QuoteRequestPreviewResponse(BaseModel):
    quote_request: QuoteRequest
    quote_preview: dict
