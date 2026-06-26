from pydantic import BaseModel, Field


class CompetitorCreate(BaseModel):
    name: str = Field(min_length=1)
    competitor_type: str = Field(default="unknown", min_length=1)
    description: str = ""
    is_active: bool = True


class CompetitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    competitor_type: str | None = Field(default=None, min_length=1)
    description: str | None = None
    is_active: bool | None = None


class CompetitorPriceCreate(BaseModel):
    competitor_id: int = Field(ge=1)
    product_id: int = Field(ge=1)
    quantity: int = Field(ge=1)
    option_summary: str = Field(min_length=1)
    price: float = Field(gt=0)
    source_note: str = ""
    collected_at: str | None = None


class CompetitorPriceUpdate(BaseModel):
    competitor_id: int | None = Field(default=None, ge=1)
    product_id: int | None = Field(default=None, ge=1)
    quantity: int | None = Field(default=None, ge=1)
    option_summary: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, gt=0)
    source_note: str | None = None
    collected_at: str | None = None


class MarketReferencePrice(BaseModel):
    competitor_name: str
    competitor_type: str
    price: float
    source_note: str
    collected_at: str


class MarketReferenceSummary(BaseModel):
    lowest_price: float | None
    highest_price: float | None
    average_price: float | None
    count: int


class MarketReferenceResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    option_summary: str
    competitor_prices: list[MarketReferencePrice]
    summary: MarketReferenceSummary
