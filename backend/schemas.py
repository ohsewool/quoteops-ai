from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str


class SystemStatusResponse(BaseModel):
    service: str
    database_configured: bool
    database_type: str
    openai_configured: bool
    demo_tools_enabled: bool


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    sku: str = Field(..., min_length=1, max_length=80)
    category: str = Field(..., min_length=1, max_length=80)
    description: str | None = None
    active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    sku: str | None = Field(default=None, min_length=1, max_length=80)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    description: str | None = None
    active: bool | None = None


class ProductResponse(ProductBase, OrmModel):
    id: int
    created_at: datetime
    updated_at: datetime


class CompetitorBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    channel: str = Field(..., min_length=1, max_length=80)
    notes: str | None = None
    active: bool = True


class CompetitorCreate(CompetitorBase):
    pass


class CompetitorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    channel: str | None = Field(default=None, min_length=1, max_length=80)
    notes: str | None = None
    active: bool | None = None


class CompetitorResponse(CompetitorBase, OrmModel):
    id: int
    created_at: datetime
    updated_at: datetime


class CompetitorPriceCreate(BaseModel):
    competitor_id: int
    product_id: int
    reference_price: float = Field(..., gt=0)
    source_note: str | None = None
    observed_at: datetime | None = None


class CompetitorPriceResponse(OrmModel):
    id: int
    competitor_id: int
    product_id: int
    reference_price: float
    source_note: str | None
    observed_at: datetime
    created_at: datetime


class CostProfileBase(BaseModel):
    product_id: int
    material_cost: float = Field(..., ge=0)
    labor_cost: float = Field(..., ge=0)
    overhead_cost: float = Field(..., ge=0)
    target_margin_rate: float = Field(..., ge=0, le=1)
    active: bool = True


class CostProfileCreate(CostProfileBase):
    pass


class CostProfileUpdate(BaseModel):
    product_id: int | None = None
    material_cost: float | None = Field(default=None, ge=0)
    labor_cost: float | None = Field(default=None, ge=0)
    overhead_cost: float | None = Field(default=None, ge=0)
    target_margin_rate: float | None = Field(default=None, ge=0, le=1)
    active: bool | None = None


class CostProfileResponse(CostProfileBase, OrmModel):
    id: int
    created_at: datetime
    updated_at: datetime


PriceTableStatus = Literal["draft", "active", "archived"]


class PriceTableBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=140)
    status: PriceTableStatus = "draft"
    description: str | None = None


class PriceTableCreate(PriceTableBase):
    pass


class PriceTableUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=140)
    status: PriceTableStatus | None = None
    description: str | None = None


class PriceTableResponse(PriceTableBase, OrmModel):
    id: int
    created_at: datetime
    updated_at: datetime


class PriceTableItemCreate(BaseModel):
    product_id: int
    price: float = Field(..., gt=0)
    margin_rate: float = Field(..., ge=0, le=1)


class PriceTableItemResponse(OrmModel):
    id: int
    price_table_id: int
    product_id: int
    price: float
    margin_rate: float
    created_at: datetime


class QuotePreviewRequest(BaseModel):
    product_id: int
    quantity: int
    material_cost: float | None = None
    labor_cost: float | None = None
    overhead_cost: float | None = None
    target_margin_rate: float | None = None


class QuotePreviewResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_cost: float
    total_cost: float
    target_margin_rate: float
    suggested_unit_price: float
    suggested_total_price: float
    estimated_gross_profit: float
    estimated_margin_rate: float
    calculation_notes: list[str]
