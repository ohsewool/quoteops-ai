from __future__ import annotations

from pydantic import BaseModel, Field


class FieldError(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    detail: str
    code: str
    field_errors: list[FieldError] = Field(default_factory=list)
    request_id: str
