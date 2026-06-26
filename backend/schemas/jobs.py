from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class PricingAnalysisWorkflowRequest(BaseModel):
    product_id: int | None = Field(default=None, ge=1)
    product_slug: str | None = Field(default=None, min_length=1)
    option_summary: str = Field(min_length=1)
    quantities: list[int] = Field(min_length=1)
    strategy_name: str | None = Field(default="balanced_market", min_length=1)
    strategy_template_id: int | None = Field(default=None, ge=1)
    run_validation: bool = True
    run_ai_explanation: bool = True

    @model_validator(mode="after")
    def validate_workflow_input(self):
        if self.product_id is None and not self.product_slug:
            raise ValueError("Either product_id or product_slug is required.")
        if any(quantity <= 0 for quantity in self.quantities):
            raise ValueError("Quantities must be positive.")
        return self


class AgentJob(BaseModel):
    id: int
    job_type: str
    status: str
    title: str
    input: dict[str, Any]
    result: dict[str, Any] | None
    error_message: str | None
    created_by: str | None
    created_at: str
    updated_at: str
    started_at: str | None
    completed_at: str | None


class AgentJobStep(BaseModel):
    id: int
    job_id: int
    step_type: str
    status: str
    title: str
    message: str
    metadata: dict[str, Any] | None
    started_at: str | None
    completed_at: str | None
    created_at: str


class AgentJobListResponse(BaseModel):
    items: list[AgentJob]
    total: int
    limit: int
    offset: int


class PricingAnalysisWorkflowResponse(BaseModel):
    job: AgentJob
    steps: list[AgentJobStep]
