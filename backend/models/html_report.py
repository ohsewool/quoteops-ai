"""Immutable, approved-Quote report artifacts for the V2 Report Center."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base


class HtmlReport(Base):
    """A rendered, read-only artifact grounded in one approved Quote revision."""

    __tablename__ = "html_reports"
    __table_args__ = (
        CheckConstraint("report_type = 'approved_quote'", name="ck_html_reports_supported_type"),
        CheckConstraint("length(btrim(title)) > 0", name="ck_html_reports_nonblank_title"),
        CheckConstraint("length(btrim(summary_text)) > 0", name="ck_html_reports_nonblank_summary"),
        CheckConstraint("length(html_content) > 0", name="ck_html_reports_nonempty_content"),
        CheckConstraint("length(content_sha256) = 64", name="ck_html_reports_content_sha256"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(48), nullable=False, default="approved_quote")
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    quote_id: Mapped[int] = mapped_column(
        ForeignKey("quotes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_quote_revision_id: Mapped[int] = mapped_column(
        ForeignKey("quote_revisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    approval_request_id: Mapped[int] = mapped_column(
        ForeignKey("approval_requests.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    approval_decision_id: Mapped[int] = mapped_column(
        ForeignKey("approval_decisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    predecessor_report_id: Mapped[int | None] = mapped_column(
        ForeignKey("html_reports.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    html_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
