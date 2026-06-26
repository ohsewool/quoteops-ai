from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


def _slug(value: str) -> str:
    return value.strip().lower()


class StrategyTemplateBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    product_id: int | None = Field(default=None, ge=1)
    product_category_id: int | None = Field(default=None, ge=1)
    strategy_name: str = Field(min_length=1)
    market_position: str = Field(default="balanced", min_length=1)
    margin_bias: str = Field(default="medium", min_length=1)
    competitor_weight_mode: str = Field(default="balanced_reference", min_length=1)
    rounding_unit: int = Field(default=100)
    is_default: bool = False
    is_active: bool = True

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        return _slug(value)


class StrategyTemplateCreate(StrategyTemplateBase):
    pass


class StrategyTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    slug: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    product_id: int | None = Field(default=None, ge=1)
    product_category_id: int | None = Field(default=None, ge=1)
    strategy_name: str | None = Field(default=None, min_length=1)
    market_position: str | None = Field(default=None, min_length=1)
    margin_bias: str | None = Field(default=None, min_length=1)
    competitor_weight_mode: str | None = Field(default=None, min_length=1)
    rounding_unit: int | None = None
    is_default: bool | None = None
    is_active: bool | None = None

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str | None) -> str | None:
        return _slug(value) if value is not None else value


class StrategyTemplate(BaseModel):
    id: int
    name: str
    slug: str
    description: str
    product_id: int | None
    product_name: str | None = None
    product_category_id: int | None
    product_category_name: str | None = None
    strategy_name: str
    market_position: str
    margin_bias: str
    competitor_weight_mode: str
    rounding_unit: int
    is_default: bool
    is_active: bool
    created_at: str
    updated_at: str
