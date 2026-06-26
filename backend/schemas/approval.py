from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    reviewer_name: str | None = Field(default=None, max_length=120)
    reviewer_note: str | None = Field(default=None, max_length=1000)


class ApprovalActionResponse(BaseModel):
    approval_id: int
    candidate_table_id: int
    product_id: int
    action: str
    status: str
    candidate_status: str
    created_price_table_id: int | None
    message: str


class ApprovalRecord(BaseModel):
    id: int
    candidate_table_id: int
    product_id: int
    product_name: str
    action: str
    status: str
    reviewer_name: str | None
    reviewer_note: str | None
    created_price_table_id: int | None
    created_at: str
    updated_at: str
