"""Persistent, reviewable approval lineage for a Quote pricing decision."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.approvals import ApprovalStatus
from backend.domain.money import MONEY_PRECISION, MONEY_SCALE, RATE_PRECISION, RATE_SCALE
from backend.domain.pricing import RiskLevel, ValidationStatus
from backend.models.base import Base


MONEY_COLUMN = Numeric(MONEY_PRECISION, MONEY_SCALE)
RATE_COLUMN = Numeric(RATE_PRECISION, RATE_SCALE)


def _approval_status_enum() -> Enum:
    return Enum(
        ApprovalStatus,
        name="approval_status",
        native_enum=True,
        values_callable=lambda enum_class: [member.value for member in enum_class],
    )


def _validation_status_enum() -> Enum:
    return Enum(
        ValidationStatus,
        name="validation_status",
        native_enum=True,
        values_callable=lambda enum_class: [member.value for member in enum_class],
    )


def _risk_level_enum() -> Enum:
    return Enum(
        RiskLevel,
        name="risk_level",
        native_enum=True,
        values_callable=lambda enum_class: [member.value for member in enum_class],
    )


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        UniqueConstraint("pricing_check_id", "price_candidate_id", name="uq_approval_requests_pricing_candidate"),
        CheckConstraint("quote_version > 0", name="ck_approval_requests_positive_quote_version"),
        CheckConstraint("candidate_total_price >= 0", name="ck_approval_requests_nonnegative_candidate_price"),
        CheckConstraint("candidate_gross_profit >= 0", name="ck_approval_requests_nonnegative_candidate_profit"),
        CheckConstraint(
            "candidate_margin_rate >= 0 AND candidate_margin_rate < 1",
            name="ck_approval_requests_valid_candidate_margin",
        ),
        CheckConstraint("currency = 'KRW'", name="ck_approval_requests_currency_krw"),
        CheckConstraint("version > 0", name="ck_approval_requests_positive_version"),
        CheckConstraint(
            "request_reason IS NULL OR length(btrim(request_reason)) > 0",
            name="ck_approval_requests_nonblank_request_reason",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_id: Mapped[int] = mapped_column(
        ForeignKey("quotes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quote_revision_id: Mapped[int] = mapped_column(
        ForeignKey("quote_revisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quote_version: Mapped[int] = mapped_column(Integer, nullable=False)
    pricing_check_id: Mapped[int] = mapped_column(
        ForeignKey("pricing_checks.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    price_candidate_id: Mapped[int] = mapped_column(
        ForeignKey("price_candidates.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    requester_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    status: Mapped[ApprovalStatus] = mapped_column(
        _approval_status_enum(), nullable=False, default=ApprovalStatus.PENDING, index=True
    )
    validation_status: Mapped[ValidationStatus] = mapped_column(_validation_status_enum(), nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(_risk_level_enum(), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KRW")
    candidate_total_price: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    candidate_gross_profit: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    candidate_margin_rate: Mapped[Decimal] = mapped_column(RATE_COLUMN, nullable=False)
    request_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ApprovalDecision(Base):
    __tablename__ = "approval_decisions"
    __table_args__ = (
        UniqueConstraint("approval_request_id", name="uq_approval_decisions_request"),
        CheckConstraint(
            "decision IN ('approved', 'rejected')",
            name="ck_approval_decisions_terminal_decision",
        ),
        CheckConstraint(
            "decision <> 'rejected' OR length(btrim(reason)) > 0",
            name="ck_approval_decisions_rejection_reason",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    approval_request_id: Mapped[int] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    decision: Mapped[ApprovalStatus] = mapped_column(_approval_status_enum(), nullable=False)
    reviewer_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    result_quote_revision_id: Mapped[int] = mapped_column(
        ForeignKey("quote_revisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    demo_self_approval_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
