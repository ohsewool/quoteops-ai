"""Approval workflow vocabulary for immutable V2 pricing evidence."""

from __future__ import annotations

from enum import StrEnum


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


DECISION_STATUSES = frozenset({ApprovalStatus.APPROVED, ApprovalStatus.REJECTED})
TERMINAL_APPROVAL_STATUSES = frozenset(
    {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.CANCELLED}
)


def approval_is_terminal(status: ApprovalStatus) -> bool:
    return status in TERMINAL_APPROVAL_STATUSES
