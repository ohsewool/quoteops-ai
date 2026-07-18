"""PostgreSQL models for V2 source data and immutable pricing evidence."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.domain.customer_requests import ProductCode
from backend.domain.money import MONEY_PRECISION, MONEY_SCALE, RATE_PRECISION, RATE_SCALE
from backend.domain.pricing import (
    CompetitorType,
    PricingCheckStatus,
    ReferencePriceBasis,
    RiskLevel,
    ValidationSeverity,
    ValidationStatus,
)
from backend.models.base import Base

MONEY_COLUMN = Numeric(MONEY_PRECISION, MONEY_SCALE)
RATE_COLUMN = Numeric(RATE_PRECISION, RATE_SCALE)


def _product_code_enum() -> Enum:
    return Enum(
        ProductCode,
        name="product_code",
        native_enum=True,
        values_callable=lambda enum_class: [member.value for member in enum_class],
    )


def _competitor_type_enum() -> Enum:
    return Enum(
        CompetitorType,
        name="competitor_type",
        native_enum=True,
        values_callable=lambda enum_class: [member.value for member in enum_class],
    )


def _reference_price_basis_enum() -> Enum:
    return Enum(
        ReferencePriceBasis,
        name="reference_price_basis",
        native_enum=True,
        values_callable=lambda enum_class: [member.value for member in enum_class],
    )


def _pricing_check_status_enum() -> Enum:
    return Enum(
        PricingCheckStatus,
        name="pricing_check_status",
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


def _validation_severity_enum() -> Enum:
    return Enum(
        ValidationSeverity,
        name="validation_severity",
        native_enum=True,
        values_callable=lambda enum_class: [member.value for member in enum_class],
    )


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("code", name="uq_products_code"),
        CheckConstraint("version > 0", name="ck_products_positive_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[ProductCode] = mapped_column(_product_code_enum(), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CostProfile(Base):
    __tablename__ = "cost_profiles"
    __table_args__ = (
        CheckConstraint("material_cost >= 0", name="ck_cost_profiles_nonnegative_material_cost"),
        CheckConstraint("labor_cost >= 0", name="ck_cost_profiles_nonnegative_labor_cost"),
        CheckConstraint("overhead_cost >= 0", name="ck_cost_profiles_nonnegative_overhead_cost"),
        CheckConstraint("target_margin_rate >= 0 AND target_margin_rate < 1", name="ck_cost_profiles_valid_target_margin"),
        CheckConstraint("version > 0", name="ck_cost_profiles_positive_version"),
        Index(
            "uq_cost_profiles_one_active_per_product",
            "product_id",
            unique=True,
            postgresql_where=text("active"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    material_cost: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    labor_cost: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    overhead_cost: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    target_margin_rate: Mapped[Decimal] = mapped_column(RATE_COLUMN, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Competitor(Base):
    __tablename__ = "competitors"
    __table_args__ = (CheckConstraint("version > 0", name="ck_competitors_positive_version"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    competitor_type: Mapped[CompetitorType] = mapped_column(_competitor_type_enum(), nullable=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class CompetitorReference(Base):
    __tablename__ = "competitor_references"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_competitor_references_positive_quantity"),
        CheckConstraint("reference_price >= 0", name="ck_competitor_references_nonnegative_price"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    competitor_id: Mapped[int] = mapped_column(ForeignKey("competitors.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    price_basis: Mapped[ReferencePriceBasis] = mapped_column(_reference_price_basis_enum(), nullable=False)
    reference_price: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PricingCheck(Base):
    __tablename__ = "pricing_checks"
    __table_args__ = (
        CheckConstraint("quote_version > 0", name="ck_pricing_checks_positive_quote_version"),
        CheckConstraint("total_cost >= 0", name="ck_pricing_checks_nonnegative_total_cost"),
        CheckConstraint("selected_total_price >= 0", name="ck_pricing_checks_nonnegative_selected_total_price"),
        CheckConstraint("selected_gross_profit >= 0", name="ck_pricing_checks_nonnegative_selected_gross_profit"),
        CheckConstraint("selected_margin_rate >= 0 AND selected_margin_rate < 1", name="ck_pricing_checks_valid_selected_margin"),
        CheckConstraint("minimum_margin_rate >= 0 AND minimum_margin_rate < 1", name="ck_pricing_checks_valid_minimum_margin"),
        CheckConstraint("currency = 'KRW'", name="ck_pricing_checks_currency_krw"),
        CheckConstraint(
            "selected_strategy IN ('low_margin', 'target_margin', 'premium_margin')",
            name="ck_pricing_checks_supported_strategy",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id", ondelete="RESTRICT"), nullable=False, index=True)
    quote_revision_id: Mapped[int] = mapped_column(ForeignKey("quote_revisions.id", ondelete="RESTRICT"), nullable=False, index=True)
    quote_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[PricingCheckStatus] = mapped_column(_pricing_check_status_enum(), nullable=False, index=True)
    selected_strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KRW")
    total_cost: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    selected_total_price: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    selected_gross_profit: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    selected_margin_rate: Mapped[Decimal] = mapped_column(RATE_COLUMN, nullable=False)
    minimum_margin_rate: Mapped[Decimal] = mapped_column(RATE_COLUMN, nullable=False)
    formula_version: Mapped[str] = mapped_column(String(64), nullable=False)
    validation_rule_version: Mapped[str] = mapped_column(String(64), nullable=False)
    rounding_policy_version: Mapped[str] = mapped_column(String(64), nullable=False)
    cost_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    competitor_context_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)


class PriceCandidate(Base):
    __tablename__ = "price_candidates"
    __table_args__ = (
        UniqueConstraint("pricing_check_id", "position", name="uq_price_candidates_check_position"),
        CheckConstraint("position > 0", name="ck_price_candidates_positive_position"),
        CheckConstraint("margin_rate >= 0 AND margin_rate < 1", name="ck_price_candidates_valid_margin"),
        CheckConstraint("total_cost >= 0", name="ck_price_candidates_nonnegative_total_cost"),
        CheckConstraint("total_price >= 0", name="ck_price_candidates_nonnegative_total_price"),
        CheckConstraint("estimated_gross_profit >= 0", name="ck_price_candidates_nonnegative_gross_profit"),
        CheckConstraint("estimated_margin_rate >= 0 AND estimated_margin_rate < 1", name="ck_price_candidates_valid_estimated_margin"),
        CheckConstraint(
            "strategy IN ('low_margin', 'target_margin', 'premium_margin')",
            name="ck_price_candidates_supported_strategy",
        ),
        Index(
            "uq_price_candidates_one_selected_per_check",
            "pricing_check_id",
            unique=True,
            postgresql_where=text("is_selected"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pricing_check_id: Mapped[int] = mapped_column(ForeignKey("pricing_checks.id", ondelete="RESTRICT"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    strategy: Mapped[str] = mapped_column(String(64), nullable=False)
    margin_rate: Mapped[Decimal] = mapped_column(RATE_COLUMN, nullable=False)
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    total_cost: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    total_price: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    estimated_gross_profit: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    estimated_margin_rate: Mapped[Decimal] = mapped_column(RATE_COLUMN, nullable=False)
    notes_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PriceCandidateLine(Base):
    __tablename__ = "price_candidate_lines"
    __table_args__ = (
        UniqueConstraint("price_candidate_id", "position", name="uq_price_candidate_lines_candidate_position"),
        CheckConstraint("position > 0", name="ck_price_candidate_lines_positive_position"),
        CheckConstraint("quantity > 0", name="ck_price_candidate_lines_positive_quantity"),
        CheckConstraint("unit_cost >= 0", name="ck_price_candidate_lines_nonnegative_unit_cost"),
        CheckConstraint("unit_price >= 0", name="ck_price_candidate_lines_nonnegative_unit_price"),
        CheckConstraint("total_cost >= 0", name="ck_price_candidate_lines_nonnegative_total_cost"),
        CheckConstraint("total_price >= 0", name="ck_price_candidate_lines_nonnegative_total_price"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    price_candidate_id: Mapped[int] = mapped_column(ForeignKey("price_candidates.id", ondelete="RESTRICT"), nullable=False, index=True)
    source_quote_revision_line_id: Mapped[int] = mapped_column(
        ForeignKey("quote_revision_lines.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    product_code: Mapped[ProductCode] = mapped_column(_product_code_enum(), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_cost: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    total_price: Mapped[Decimal] = mapped_column(MONEY_COLUMN, nullable=False)
    calculation_inputs_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class PriceValidationResult(Base):
    __tablename__ = "price_validation_results"
    __table_args__ = (
        UniqueConstraint("price_candidate_id", name="uq_price_validation_results_candidate"),
        CheckConstraint("minimum_margin_rate >= 0 AND minimum_margin_rate < 1", name="ck_price_validation_results_valid_minimum_margin"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    price_candidate_id: Mapped[int] = mapped_column(ForeignKey("price_candidates.id", ondelete="RESTRICT"), nullable=False, index=True)
    validation_status: Mapped[ValidationStatus] = mapped_column(_validation_status_enum(), nullable=False, index=True)
    risk_level: Mapped[RiskLevel] = mapped_column(_risk_level_enum(), nullable=False, index=True)
    minimum_margin_rate: Mapped[Decimal] = mapped_column(RATE_COLUMN, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PriceValidationCheck(Base):
    __tablename__ = "price_validation_checks"
    __table_args__ = (
        UniqueConstraint("price_validation_result_id", "code", name="uq_price_validation_checks_result_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    price_validation_result_id: Mapped[int] = mapped_column(
        ForeignKey("price_validation_results.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(96), nullable=False)
    severity: Mapped[ValidationSeverity] = mapped_column(_validation_severity_enum(), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    message: Mapped[str] = mapped_column(String(280), nullable=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
