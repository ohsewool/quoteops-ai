from pydantic import BaseModel, Field, model_validator


class QuotePreviewRequest(BaseModel):
    product_id: int | None = Field(default=None, ge=1)
    product_slug: str | None = None
    quantity: int = Field(ge=1)
    option_summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def require_product_identifier(self):
        if self.product_id is None and not self.product_slug:
            raise ValueError("Either product_id or product_slug is required.")
        return self


class QuotePreviewResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    option_summary: str
    quote_price: float
    unit_price: float
    calculation_source: str
    price_table_name: str | None
    warnings: list[str]
