"""Grounded copilot vocabulary with no pricing or workflow authority."""

from __future__ import annotations

from enum import StrEnum


class CopilotPurpose(StrEnum):
    CANDIDATE_EXPLANATION = "candidate_explanation"
    VALIDATION_SUMMARY = "validation_summary"
    APPROVAL_REASON_DRAFT = "approval_reason_draft"
    REJECTION_REVISION_SUGGESTION = "rejection_revision_suggestion"
    REPORT_SUMMARY_DRAFT = "report_summary_draft"


class CopilotGenerationMode(StrEnum):
    PROVIDER = "provider"
    FALLBACK = "fallback"
    UNAVAILABLE = "unavailable"
