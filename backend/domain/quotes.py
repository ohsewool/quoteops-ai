from __future__ import annotations

from enum import StrEnum


class QuoteStatus(StrEnum):
    DRAFT = "draft"
    PRICING_REVIEW = "pricing_review"
    BLOCKED = "blocked"
    APPROVAL_PENDING = "approval_pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


EDITABLE_QUOTE_STATUSES = frozenset({QuoteStatus.DRAFT})
TERMINAL_QUOTE_STATUSES = frozenset({QuoteStatus.APPROVED, QuoteStatus.CANCELLED})


def quote_is_editable(status: QuoteStatus) -> bool:
    """Only a draft Quote may have metadata or current lines replaced."""

    return status in EDITABLE_QUOTE_STATUSES


def quote_is_terminal(status: QuoteStatus) -> bool:
    return status in TERMINAL_QUOTE_STATUSES
