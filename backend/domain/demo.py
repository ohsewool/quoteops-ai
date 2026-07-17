"""Explicit, non-production guided-demo state for the two V2 MVP products."""

from __future__ import annotations

from enum import StrEnum


class DemoRunStatus(StrEnum):
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"


DEMO_GUIDE_STEPS: tuple[dict[str, str], ...] = (
    {
        "key": "review_requests",
        "title": "Review the two demo requests",
        "description": "Open the seeded A3 Flyer and Product / Brand Sticker requests.",
        "deep_link": "/app/requests",
    },
    {
        "key": "create_quote",
        "title": "Create a persisted quote",
        "description": "Move each reviewed demo request into the Quote workspace.",
        "deep_link": "/app/quotes",
    },
    {
        "key": "run_pricing_check",
        "title": "Run deterministic pricing checks",
        "description": "Generate saved pricing evidence for both demo products.",
        "deep_link": "/app/pricing",
    },
    {
        "key": "request_review",
        "title": "Submit an eligible approval request",
        "description": "Use a separate reviewer for each eligible pricing record.",
        "deep_link": "/app/approvals",
    },
    {
        "key": "review_approval",
        "title": "Review the approval decision",
        "description": "Approve or reject each request with an authenticated human reviewer.",
        "deep_link": "/app/approvals",
    },
    {
        "key": "generate_report",
        "title": "Generate a grounded report",
        "description": "Create read-only reports from the approved quote revisions.",
        "deep_link": "/app/reports",
    },
)


def demo_step_count() -> int:
    return len(DEMO_GUIDE_STEPS)
