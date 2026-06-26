from pydantic import BaseModel, Field, field_validator


def _slug(value: str) -> str:
    return value.strip().lower()


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    slug: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    is_active: bool = True
    category_id: int | None = Field(default=None, ge=1)
    quantity_ladder_id: int | None = Field(default=None, ge=1)

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str) -> str:
        return _slug(value)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    slug: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None
    category_id: int | None = Field(default=None, ge=1)
    quantity_ladder_id: int | None = Field(default=None, ge=1)

    @field_validator("slug")
    @classmethod
    def normalize_slug(cls, value: str | None) -> str | None:
        return _slug(value) if value is not None else value


class ProductOptionCreate(BaseModel):
    product_id: int = Field(ge=1)
    option_type: str = Field(min_length=1, max_length=120)
    option_name: str = Field(min_length=1, max_length=160)
    option_value: str = Field(min_length=1, max_length=240)
    sort_order: int = 0
    is_active: bool = True


class ProductOptionUpdate(BaseModel):
    product_id: int | None = Field(default=None, ge=1)
    option_type: str | None = Field(default=None, min_length=1, max_length=120)
    option_name: str | None = Field(default=None, min_length=1, max_length=160)
    option_value: str | None = Field(default=None, min_length=1, max_length=240)
    sort_order: int | None = None
    is_active: bool | None = None
