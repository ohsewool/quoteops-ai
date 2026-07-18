from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.customer_requests import ProductCode
from backend.domain.money import MONEY_PRECISION, MONEY_SCALE
from backend.domain.quotes import QuoteStatus
from backend.models.base import Base


MONEY_COLUMN = Numeric(MONEY_PRECISION, MONEY_SCALE)


def _product_code_enum() -> Enum:
    return Enum(
        ProductCode,
        name="product_code",
        native_enum=True,
        values_callable=lambda enum_class: [member.value for member in enum_class],
    )


def _quote_status_enum() -> Enum:
    return Enum(
        QuoteStatus,
        name="quote_status",
        native_enum=True,
        values_callable=lambda enum_class: [member.value for member in enum_class],
    )


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (
        UniqueConstraint("quote_number", name="uq_quotes_quote_number"),
        CheckConstraint("request_quantity > 0", name="ck_quotes_positive_request_quantity"),
        CheckConstraint("source_request_version > 0", name="ck_quotes_positive_source_request_version"),
        CheckConstraint("version > 0", name="ck_quotes_positive_version"),
        CheckConstraint("current_revision_number >= 0", name="ck_quotes_nonnegative_current_revision_number"),
        CheckConstraint("total_amount >= 0", name="ck_quotes_nonnegative_total_amount"),
        CheckConstraint("currency = 'KRW'", name="ck_quotes_currency_krw"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer_request_id: Mapped[int] = mapped_column(
        ForeignKey("customer_requests.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    quote_number: Mapped[str] = mapped_column(String(48), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    contact_name_snapshot: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_product_code: Mapped[ProductCode] = mapped_column(_product_code_enum(), nullable=False, index=True)
    request_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    source_request_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[QuoteStatus] = mapped_column(
        _quote_status_enum(), nullable=False, default=QuoteStatus.DRAFT, index=True
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KRW")
    total_amount: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False, default=Decimal("0.00"))
    formula_version: Mapped[str] = mapped_column(String(64), nullable=False, default="quote-line-sum-v1")
    rounding_policy_version: Mapped[str] = mapped_column(String(64), nullable=False, default="krw-half-up-v1")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    assignee_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_revision_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class QuoteLine(Base):
    __tablename__ = "quote_lines"
    __table_args__ = (
        UniqueConstraint("quote_id", "position", name="uq_quote_lines_quote_position"),
        CheckConstraint("position > 0", name="ck_quote_lines_positive_position"),
        CheckConstraint("quantity > 0", name="ck_quote_lines_positive_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_quote_lines_nonnegative_unit_price"),
        CheckConstraint("line_total >= 0", name="ck_quote_lines_nonnegative_line_total"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_id: Mapped[int] = mapped_column(
        ForeignKey("quotes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    product_code: Mapped[ProductCode] = mapped_column(_product_code_enum(), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    options_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class QuoteRevision(Base):
    __tablename__ = "quote_revisions"
    __table_args__ = (
        UniqueConstraint("quote_id", "revision_number", name="uq_quote_revisions_quote_revision_number"),
        CheckConstraint("revision_number > 0", name="ck_quote_revisions_positive_revision_number"),
        CheckConstraint("quote_version > 0", name="ck_quote_revisions_positive_quote_version"),
        CheckConstraint("request_quantity > 0", name="ck_quote_revisions_positive_request_quantity"),
        CheckConstraint("source_request_version > 0", name="ck_quote_revisions_positive_source_request_version"),
        CheckConstraint("line_count >= 0", name="ck_quote_revisions_nonnegative_line_count"),
        CheckConstraint("total_amount >= 0", name="ck_quote_revisions_nonnegative_total_amount"),
        CheckConstraint("currency = 'KRW'", name="ck_quote_revisions_currency_krw"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_id: Mapped[int] = mapped_column(
        ForeignKey("quotes.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    quote_version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_request_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[QuoteStatus] = mapped_column(_quote_status_enum(), nullable=False)
    quote_number: Mapped[str] = mapped_column(String(48), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_name_snapshot: Mapped[str] = mapped_column(String(160), nullable=False)
    contact_name_snapshot: Mapped[str | None] = mapped_column(String(128), nullable=True)
    request_product_code: Mapped[ProductCode] = mapped_column(_product_code_enum(), nullable=False)
    request_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KRW")
    total_amount: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    formula_version: Mapped[str] = mapped_column(String(64), nullable=False)
    rounding_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    line_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )


class QuoteRevisionLine(Base):
    __tablename__ = "quote_revision_lines"
    __table_args__ = (
        UniqueConstraint("quote_revision_id", "position", name="uq_quote_revision_lines_revision_position"),
        CheckConstraint("position > 0", name="ck_quote_revision_lines_positive_position"),
        CheckConstraint("quantity > 0", name="ck_quote_revision_lines_positive_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_quote_revision_lines_nonnegative_unit_price"),
        CheckConstraint("line_total >= 0", name="ck_quote_revision_lines_nonnegative_line_total"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_revision_id: Mapped[int] = mapped_column(
        ForeignKey("quote_revisions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    source_quote_line_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    product_code: Mapped[ProductCode] = mapped_column(_product_code_enum(), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    line_total: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    options_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
