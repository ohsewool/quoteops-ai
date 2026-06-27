from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db import Base


def utc_now() -> datetime:
    return datetime.utcnow()


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sku: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    competitor_prices = relationship("CompetitorPrice", back_populates="product")
    cost_profiles = relationship("CostProfile", back_populates="product")
    approval_requests = relationship("PriceApprovalRequest", back_populates="product")
    price_table_items = relationship("PriceTableItem", back_populates="product")
    pricing_simulations = relationship("PricingSimulation", back_populates="product")


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    channel: Mapped[str] = mapped_column(String(80), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    prices = relationship("CompetitorPrice", back_populates="competitor")


class CompetitorPrice(Base):
    __tablename__ = "competitor_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    competitor_id: Mapped[int] = mapped_column(
        ForeignKey("competitors.id"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    reference_price: Mapped[float] = mapped_column(Float, nullable=False)
    source_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    competitor = relationship("Competitor", back_populates="prices")
    product = relationship("Product", back_populates="competitor_prices")


class CostProfile(Base):
    __tablename__ = "cost_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    material_cost: Mapped[float] = mapped_column(Float, nullable=False)
    labor_cost: Mapped[float] = mapped_column(Float, nullable=False)
    overhead_cost: Mapped[float] = mapped_column(Float, nullable=False)
    target_margin_rate: Mapped[float] = mapped_column(Float, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    product = relationship("Product", back_populates="cost_profiles")


class PriceTable(Base):
    __tablename__ = "price_tables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )

    items = relationship("PriceTableItem", back_populates="price_table")


class PriceTableItem(Base):
    __tablename__ = "price_table_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    price_table_id: Mapped[int] = mapped_column(
        ForeignKey("price_tables.id"), nullable=False, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    price: Mapped[float] = mapped_column(Float, nullable=False)
    margin_rate: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    price_table = relationship("PriceTable", back_populates="items")
    product = relationship("Product", back_populates="price_table_items")


class PriceApprovalRequest(Base):
    __tablename__ = "price_approval_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    proposed_unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    proposed_total_price: Mapped[float] = mapped_column(Float, nullable=False)
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_gross_profit: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_margin_rate: Mapped[float] = mapped_column(Float, nullable=False)
    minimum_margin_rate: Mapped[float] = mapped_column(Float, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    reviewer_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    product = relationship("Product", back_populates="approval_requests")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now, nullable=False
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    actor_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    actor_username: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)


class PricingSimulation(Base):
    __tablename__ = "pricing_simulations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False, index=True
    )
    unit_cost: Mapped[float] = mapped_column(Float, nullable=False)
    include_competitor_context: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    competitor_context_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_username: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    product = relationship("Product", back_populates="pricing_simulations")
    scenarios = relationship(
        "PricingSimulationScenario",
        back_populates="simulation",
        cascade="all, delete-orphan",
    )


class PricingSimulationScenario(Base):
    __tablename__ = "pricing_simulation_scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    simulation_id: Mapped[int] = mapped_column(
        ForeignKey("pricing_simulations.id"), nullable=False, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    margin_rate: Mapped[float] = mapped_column(Float, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    total_cost: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_gross_profit: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_margin_rate: Mapped[float] = mapped_column(Float, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    simulation = relationship("PricingSimulation", back_populates="scenarios")
