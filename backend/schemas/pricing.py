from pydantic import BaseModel, Field


class CostProfileCreate(BaseModel):
    product_id: int = Field(ge=1)
    quantity: int = Field(ge=1)
    option_summary: str = Field(min_length=1)
    unit_cost: float = Field(ge=0)
    fixed_cost: float = Field(ge=0)
    minimum_margin_rate: float = Field(ge=0, lt=1)
    minimum_price: float = Field(ge=0)


class CostProfileUpdate(BaseModel):
    product_id: int | None = Field(default=None, ge=1)
    quantity: int | None = Field(default=None, ge=1)
    option_summary: str | None = Field(default=None, min_length=1)
    unit_cost: float | None = Field(default=None, ge=0)
    fixed_cost: float | None = Field(default=None, ge=0)
    minimum_margin_rate: float | None = Field(default=None, ge=0, lt=1)
    minimum_price: float | None = Field(default=None, ge=0)


class PriceTableCreate(BaseModel):
    product_id: int = Field(ge=1)
    name: str = Field(min_length=1)
    status: str = "draft"
    strategy_name: str = "Manual Pricing"


class PriceTableUpdate(BaseModel):
    product_id: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, min_length=1)
    status: str | None = None
    strategy_name: str | None = Field(default=None, min_length=1)


class PriceTableItemCreate(BaseModel):
    quantity: int = Field(ge=1)
    option_summary: str = Field(min_length=1)
    final_price: float = Field(ge=0)
    margin_rate: float = Field(ge=0)


class PriceTableItemUpdate(BaseModel):
    quantity: int | None = Field(default=None, ge=1)
    option_summary: str | None = Field(default=None, min_length=1)
    final_price: float | None = Field(default=None, ge=0)
    margin_rate: float | None = Field(default=None, ge=0)
