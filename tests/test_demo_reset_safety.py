import sys
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.db import SessionLocal, create_db_and_tables
from backend.models import (
    Competitor,
    CustomerQuoteRequest,
    PriceApprovalRequest,
    PriceTable,
    Product,
    User,
)
from backend.services.demo_data_service import reset_demo_data, seed_demo_data_tools


def setup_module():
    create_db_and_tables()


def test_demo_reset_does_not_delete_or_disable_unknown_non_demo_records():
    suffix = uuid4().hex[:8]
    db = SessionLocal()
    try:
        seed_demo_data_tools(db, "admin")
        product = Product(
            name="QuoteOps Demo User Product",
            sku=f"USER-NON-DEMO-{suffix}",
            category="A3 Flyer",
            active=True,
        )
        competitor = Competitor(
            name=f"QuoteOps Demo User Competitor {suffix}",
            channel="local_shop",
            notes="User-created non-demo record.",
            active=True,
        )
        price_table = PriceTable(
            name=f"QuoteOps Demo User Price Table {suffix}",
            status="active",
            description="User-created table that must survive demo reset.",
        )
        user = User(
            username=f"security-user-{suffix}",
            display_name="Security Test User",
            role="viewer",
            password_hash="not-a-real-hash-for-test",
            active=True,
        )
        db.add_all([product, competitor, price_table, user])
        db.flush()
        quote_request = CustomerQuoteRequest(
            customer_name="Unknown Customer",
            customer_email=f"unknown-{suffix}@example.com",
            customer_company="Unknown Co",
            product_id=product.id,
            quantity=12,
            request_note="Non-demo customer request.",
            status="new",
        )
        approval_request = PriceApprovalRequest(
            product_id=product.id,
            quantity=12,
            proposed_unit_price=1000,
            proposed_total_price=12000,
            unit_cost=500,
            total_cost=6000,
            estimated_gross_profit=6000,
            estimated_margin_rate=0.5,
            minimum_margin_rate=0.3,
            validation_status="passed",
            risk_level="low",
            status="pending",
            submitted_note="User-created approval request.",
        )
        db.add_all([quote_request, approval_request])
        db.commit()
        ids = {
            "product": product.id,
            "competitor": competitor.id,
            "price_table": price_table.id,
            "user": user.id,
            "quote_request": quote_request.id,
            "approval_request": approval_request.id,
        }

        response = reset_demo_data(db)

        assert response.reset_completed is True
        db.expire_all()
        assert db.get(Product, ids["product"]).active is True
        assert db.get(Competitor, ids["competitor"]).active is True
        assert db.get(PriceTable, ids["price_table"]).status == "active"
        assert db.get(User, ids["user"]).active is True
        assert db.get(CustomerQuoteRequest, ids["quote_request"]) is not None
        assert db.get(PriceApprovalRequest, ids["approval_request"]) is not None
        assert any("Unknown" in note for note in response.safety_notes)
    finally:
        db.close()
