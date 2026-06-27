import json
from datetime import datetime

from sqlalchemy.orm import Session

from backend.db import SessionLocal
from backend.models import (
    Competitor,
    CompetitorPrice,
    CostProfile,
    PriceTable,
    PriceTableItem,
    PricingStrategyTemplate,
    Product,
    User,
)
from backend.auth import hash_password


DEMO_PRODUCTS = [
    {
        "name": "Demo A3 Flyer",
        "sku": "DEMO-A3-FLYER",
        "category": "A3 Flyer",
        "description": "Demo-only A3 flyer product for local MVP testing.",
    },
    {
        "name": "Demo Product / Brand Sticker",
        "sku": "DEMO-BRAND-STICKER",
        "category": "Product / Brand Sticker",
        "description": "Demo-only sticker product for local MVP testing.",
    },
]

DEMO_COMPETITORS = [
    {
        "name": "Demo Local Print Shop",
        "channel": "local_shop",
        "notes": "Demo reference only. Not real market data.",
    },
    {
        "name": "Demo Similar-Size Studio",
        "channel": "similar_size",
        "notes": "Demo reference only. Not real market data.",
    },
]

DEMO_USERS = [
    {
        "username": "admin",
        "display_name": "Demo Admin",
        "role": "admin",
        "password": "admin-demo-password",
    },
    {
        "username": "manager",
        "display_name": "Demo Manager",
        "role": "manager",
        "password": "manager-demo-password",
    },
    {
        "username": "viewer",
        "display_name": "Demo Viewer",
        "role": "viewer",
        "password": "viewer-demo-password",
    },
]

DEMO_STRATEGY_TEMPLATES = [
    {
        "name": "Standard Margin",
        "strategy_code": "standard_margin",
        "description": "Balanced margin strategy for normal quote operations.",
        "margin_rates": [0.25, 0.35, 0.45],
        "default_quantities": [1, 10, 50],
        "include_competitor_context_default": True,
        "risk_preference": "balanced",
        "notes": "Demo-only deterministic strategy template.",
    },
    {
        "name": "Premium Margin",
        "strategy_code": "premium_margin",
        "description": "Higher margin strategy for premium service positioning.",
        "margin_rates": [0.4, 0.5, 0.6],
        "default_quantities": [1, 10, 50],
        "include_competitor_context_default": True,
        "risk_preference": "aggressive",
        "notes": "Demo-only deterministic strategy template.",
    },
    {
        "name": "Conservative Bulk",
        "strategy_code": "conservative_bulk",
        "description": "Conservative bulk strategy for safer quantity pricing.",
        "margin_rates": [0.2, 0.25, 0.3],
        "default_quantities": [10, 50, 100],
        "include_competitor_context_default": False,
        "risk_preference": "conservative",
        "notes": "Demo-only deterministic strategy template.",
    },
]


def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        _seed_demo_data(db)
        db.commit()
    finally:
        db.close()


def _seed_demo_data(db: Session) -> None:
    _seed_demo_users(db)
    _seed_demo_strategy_templates(db)
    products: dict[str, Product] = {}
    for product_data in DEMO_PRODUCTS:
        product = db.query(Product).filter(Product.sku == product_data["sku"]).first()
        if product is None:
            product = Product(**product_data)
            db.add(product)
            db.flush()
        products[product.sku] = product

    competitors: dict[str, Competitor] = {}
    for competitor_data in DEMO_COMPETITORS:
        competitor = (
            db.query(Competitor)
            .filter(Competitor.name == competitor_data["name"])
            .first()
        )
        if competitor is None:
            competitor = Competitor(**competitor_data)
            db.add(competitor)
            db.flush()
        competitors[competitor.name] = competitor

    for product in products.values():
        exists = db.query(CostProfile).filter(CostProfile.product_id == product.id).first()
        if exists is None:
            db.add(
                CostProfile(
                    product_id=product.id,
                    material_cost=1200.0 if "FLYER" in product.sku else 400.0,
                    labor_cost=700.0 if "FLYER" in product.sku else 250.0,
                    overhead_cost=300.0 if "FLYER" in product.sku else 120.0,
                    target_margin_rate=0.35,
                )
            )

    first_product = products["DEMO-A3-FLYER"]
    second_product = products["DEMO-BRAND-STICKER"]
    for competitor in competitors.values():
        exists = (
            db.query(CompetitorPrice)
            .filter(
                CompetitorPrice.competitor_id == competitor.id,
                CompetitorPrice.product_id == first_product.id,
            )
            .first()
        )
        if exists is None:
            db.add(
                CompetitorPrice(
                    competitor_id=competitor.id,
                    product_id=first_product.id,
                    reference_price=52000.0,
                    source_note="Demo-only manual reference. Not real market data.",
                    observed_at=datetime(2026, 1, 1),
                )
            )

    draft_table = (
        db.query(PriceTable)
        .filter(PriceTable.name == "Demo Draft Price Table")
        .first()
    )
    if draft_table is None:
        draft_table = PriceTable(
            name="Demo Draft Price Table",
            status="draft",
            description="Demo-only draft table for API testing.",
        )
        db.add(draft_table)
        db.flush()

    active_table = (
        db.query(PriceTable)
        .filter(PriceTable.name == "Demo Active Price Table")
        .first()
    )
    if active_table is None:
        active_table = PriceTable(
            name="Demo Active Price Table",
            status="active",
            description="Demo-only active table for API testing. Not generated by AI.",
        )
        db.add(active_table)
        db.flush()

    _ensure_price_item(db, draft_table.id, first_product.id, 55000.0, 0.36)
    _ensure_price_item(db, draft_table.id, second_product.id, 18000.0, 0.34)
    _ensure_price_item(db, active_table.id, first_product.id, 59000.0, 0.39)
    _ensure_price_item(db, active_table.id, second_product.id, 21000.0, 0.37)


def _seed_demo_users(db: Session) -> None:
    if db.query(User).first() is not None:
        return
    for user_data in DEMO_USERS:
        db.add(
            User(
                username=user_data["username"],
                display_name=user_data["display_name"],
                role=user_data["role"],
                password_hash=hash_password(user_data["password"]),
                active=True,
            )
        )


def _seed_demo_strategy_templates(db: Session) -> None:
    for template_data in DEMO_STRATEGY_TEMPLATES:
        exists = (
            db.query(PricingStrategyTemplate)
            .filter(PricingStrategyTemplate.strategy_code == template_data["strategy_code"])
            .first()
        )
        if exists is not None:
            continue
        db.add(
            PricingStrategyTemplate(
                name=template_data["name"],
                strategy_code=template_data["strategy_code"],
                description=template_data["description"],
                margin_rates_json=json.dumps(
                    template_data["margin_rates"], separators=(",", ":")
                ),
                default_quantities_json=json.dumps(
                    template_data["default_quantities"], separators=(",", ":")
                ),
                include_competitor_context_default=template_data[
                    "include_competitor_context_default"
                ],
                risk_preference=template_data["risk_preference"],
                active=True,
                notes=template_data["notes"],
                created_by_username="system",
            )
        )


def _ensure_price_item(
    db: Session,
    price_table_id: int,
    product_id: int,
    price: float,
    margin_rate: float,
) -> None:
    exists = (
        db.query(PriceTableItem)
        .filter(
            PriceTableItem.price_table_id == price_table_id,
            PriceTableItem.product_id == product_id,
        )
        .first()
    )
    if exists is None:
        db.add(
            PriceTableItem(
                price_table_id=price_table_id,
                product_id=product_id,
                price=price,
                margin_rate=margin_rate,
            )
        )
