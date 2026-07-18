"""Immutable grounded-copilot text outputs and source metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class CopilotOutput(Base):
    __tablename__ = "copilot_outputs"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('candidate_explanation', 'validation_summary', 'approval_reason_draft', "
            "'rejection_revision_suggestion', 'report_summary_draft')",
            name="ck_copilot_outputs_supported_purpose",
        ),
        CheckConstraint("length(btrim(generated_text)) > 0", name="ck_copilot_outputs_nonblank_text"),
        CheckConstraint("length(btrim(provider_name)) > 0", name="ck_copilot_outputs_nonblank_provider"),
        CheckConstraint("length(btrim(generation_mode)) > 0", name="ck_copilot_outputs_nonblank_generation_mode"),
        CheckConstraint(
            "(purpose IN ('candidate_explanation', 'validation_summary', 'approval_reason_draft') "
            "AND pricing_check_id IS NOT NULL AND price_candidate_id IS NOT NULL) "
            "OR (purpose = 'rejection_revision_suggestion' AND approval_request_id IS NOT NULL) "
            "OR (purpose = 'report_summary_draft' AND report_id IS NOT NULL)",
            name="ck_copilot_outputs_purpose_context",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purpose: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id", ondelete="RESTRICT"), nullable=False, index=True)
    quote_revision_id: Mapped[int] = mapped_column(
        ForeignKey("quote_revisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    pricing_check_id: Mapped[int | None] = mapped_column(
        ForeignKey("pricing_checks.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    price_candidate_id: Mapped[int | None] = mapped_column(
        ForeignKey("price_candidates.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    approval_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    report_id: Mapped[int | None] = mapped_column(
        ForeignKey("html_reports.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    generated_text: Mapped[str] = mapped_column(Text, nullable=False)
    grounding_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_artifacts_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    triggered_rules_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    deterministic_fallback: Mapped[bool] = mapped_column(Boolean, nullable=False)
    generation_mode: Mapped[str] = mapped_column(String(24), nullable=False)
    provider_name: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_model: Mapped[str | None] = mapped_column(String(160), nullable=True)
    provider_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_data_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
