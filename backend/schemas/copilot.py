"""Public contracts for saved, grounded copilot text outputs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from backend.domain.copilot import CopilotGenerationMode, CopilotPurpose


class GroundedCopilotOutputCreate(BaseModel):
    purpose: CopilotPurpose
    quote_revision_id: int = Field(gt=0)
    pricing_check_id: int | None = Field(default=None, gt=0)
    price_candidate_id: int | None = Field(default=None, gt=0)
    approval_request_id: int | None = Field(default=None, gt=0)
    report_id: int | None = Field(default=None, gt=0)


class CopilotSourceArtifactResponse(BaseModel):
    artifact_type: str
    artifact_id: int
    created_at: datetime


class CopilotTriggeredRuleResponse(BaseModel):
    code: str
    severity: str
    passed: bool
    message: str


class GroundedCopilotOutputResponse(BaseModel):
    id: int
    purpose: CopilotPurpose
    quote_id: int
    quote_revision_id: int
    pricing_check_id: int | None
    price_candidate_id: int | None
    approval_request_id: int | None
    report_id: int | None
    created_by_user_id: int
    generated_text: str
    grounding: dict[str, object]
    source_artifacts: list[CopilotSourceArtifactResponse]
    triggered_rules: list[CopilotTriggeredRuleResponse]
    source_data_timestamp: datetime
    deterministic_fallback: bool
    generation_mode: CopilotGenerationMode
    provider_name: str
    provider_model: str | None
    provider_metadata: dict[str, object]
    generated_at: datetime
    created_at: datetime
