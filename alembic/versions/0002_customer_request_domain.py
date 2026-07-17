"""Create the V2 customer-request workflow domain.

Revision ID: 0002_customer_request_domain
Revises: 0001_security_foundation
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_customer_request_domain"
down_revision = "0001_security_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    request_status = sa.Enum(
        "new", "reviewing", "quoted", "closed", "cancelled", name="customer_request_status"
    )
    product_code = sa.Enum("a3_flyer", "brand_sticker", name="product_code")
    op.create_table(
        "customer_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_name", sa.String(length=160), nullable=False),
        sa.Column("contact_name", sa.String(length=128), nullable=True),
        sa.Column("product_code", product_code, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", request_status, nullable=False, server_default=sa.text("'new'")),
        sa.Column("assignee_user_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("quantity > 0", name="ck_customer_requests_positive_quantity"),
        sa.CheckConstraint("version > 0", name="ck_customer_requests_positive_version"),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_customer_requests_assignee_user_id", "customer_requests", ["assignee_user_id"])
    op.create_index("ix_customer_requests_created_at", "customer_requests", ["created_at"])
    op.create_index("ix_customer_requests_due_date", "customer_requests", ["due_date"])
    op.create_index("ix_customer_requests_product_code", "customer_requests", ["product_code"])
    op.create_index("ix_customer_requests_status", "customer_requests", ["status"])


def downgrade() -> None:
    op.drop_table("customer_requests")
    sa.Enum("new", "reviewing", "quoted", "closed", "cancelled", name="customer_request_status").drop(
        op.get_bind(), checkfirst=True
    )
    sa.Enum("a3_flyer", "brand_sticker", name="product_code").drop(op.get_bind(), checkfirst=True)
