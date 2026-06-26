from pydantic import BaseModel, ConfigDict, Field


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Product(ReadModel):
    id: int
    category_id: int | None = None
    category_name: str | None = None
    quantity_ladder_id: int | None = None
    quantity_ladder_name: str | None = None
    name: str
    slug: str
    description: str
    is_active: bool
    created_at: str
    updated_at: str


class ProductOption(ReadModel):
    id: int
    product_id: int
    option_type: str
    option_name: str
    option_value: str
    sort_order: int
    is_active: bool
    created_at: str
    updated_at: str


class ProductDetail(Product):
    options: list[ProductOption]


class Competitor(ReadModel):
    id: int
    name: str
    competitor_type: str
    description: str
    is_active: bool
    created_at: str
    updated_at: str


class CompetitorPrice(ReadModel):
    id: int
    competitor_id: int
    product_id: int
    quantity: int
    option_summary: str
    price: float
    source_note: str
    collected_at: str
    created_at: str
    updated_at: str


class CostProfile(ReadModel):
    id: int
    product_id: int
    quantity: int
    option_summary: str
    unit_cost: float
    fixed_cost: float
    minimum_margin_rate: float
    minimum_price: float
    created_at: str
    updated_at: str


class PriceTableItem(ReadModel):
    id: int
    price_table_id: int
    quantity: int
    option_summary: str
    final_price: float
    margin_rate: float
    created_at: str
    updated_at: str


class PriceTable(ReadModel):
    id: int
    product_id: int
    name: str
    status: str
    strategy_name: str
    created_at: str
    updated_at: str
    items: list[PriceTableItem] = Field(default_factory=list)


class ProductCategory(ReadModel):
    id: int
    name: str
    slug: str
    description: str
    sort_order: int
    is_active: bool
    created_at: str
    updated_at: str


class QuantityLadder(ReadModel):
    id: int
    name: str
    slug: str
    quantities: list[int]
    description: str
    created_at: str
    updated_at: str
