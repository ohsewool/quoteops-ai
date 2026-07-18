"""Create the V2 persistent Quote and immutable revision domain.

Revision ID: 0003_quote_domain
Revises: 0002_customer_request_domain
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0003_quote_domain"
down_revision = "0002_customer_request_domain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    quote_status = postgresql.ENUM(
        "draft",
        "pricing_review",
        "blocked",
        "approval_pending",
        "approved",
        "rejected",
        "cancelled",
        name="quote_status",
        create_type=False,
    )
    product_code = postgresql.ENUM(
        "a3_flyer", "brand_sticker", name="product_code", create_type=False
    )
    quote_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "quotes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_request_id", sa.Integer(), nullable=False),
        sa.Column("quote_number", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("customer_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("contact_name_snapshot", sa.String(length=128), nullable=True),
        sa.Column("request_product_code", product_code, nullable=False),
        sa.Column("request_quantity", sa.Integer(), nullable=False),
        sa.Column("source_request_version", sa.Integer(), nullable=False),
        sa.Column("status", quote_status, nullable=False, server_default=sa.text("'draft'")),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default=sa.text("'KRW'")),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=2), nullable=False, server_default=sa.text("0")),
        sa.Column("formula_version", sa.String(length=64), nullable=False, server_default=sa.text("'quote-line-sum-v1'")),
        sa.Column("rounding_policy_version", sa.String(length=64), nullable=False, server_default=sa.text("'krw-half-up-v1'")),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assignee_user_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("current_revision_number", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("request_quantity > 0", name="ck_quotes_positive_request_quantity"),
        sa.CheckConstraint("source_request_version > 0", name="ck_quotes_positive_source_request_version"),
        sa.CheckConstraint("version > 0", name="ck_quotes_positive_version"),
        sa.CheckConstraint("current_revision_number >= 0", name="ck_quotes_nonnegative_current_revision_number"),
        sa.CheckConstraint("total_amount >= 0", name="ck_quotes_nonnegative_total_amount"),
        sa.CheckConstraint("currency = 'KRW'", name="ck_quotes_currency_krw"),
        sa.ForeignKeyConstraint(["customer_request_id"], ["customer_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assignee_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("quote_number", name="uq_quotes_quote_number"),
    )
    op.create_index("ix_quotes_assignee_user_id", "quotes", ["assignee_user_id"])
    op.create_index("ix_quotes_created_at", "quotes", ["created_at"])
    op.create_index("ix_quotes_customer_name_snapshot", "quotes", ["customer_name_snapshot"])
    op.create_index("ix_quotes_customer_request_id", "quotes", ["customer_request_id"])
    op.create_index("ix_quotes_quote_number", "quotes", ["quote_number"], unique=True)
    op.create_index("ix_quotes_request_product_code", "quotes", ["request_product_code"])
    op.create_index("ix_quotes_status", "quotes", ["status"])

    op.create_table(
        "quote_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quote_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("product_code", product_code, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("options_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("position > 0", name="ck_quote_lines_positive_position"),
        sa.CheckConstraint("quantity > 0", name="ck_quote_lines_positive_quantity"),
        sa.CheckConstraint("unit_price >= 0", name="ck_quote_lines_nonnegative_unit_price"),
        sa.CheckConstraint("line_total >= 0", name="ck_quote_lines_nonnegative_line_total"),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("quote_id", "position", name="uq_quote_lines_quote_position"),
    )
    op.create_index("ix_quote_lines_quote_id", "quote_lines", ["quote_id"])

    op.create_table(
        "quote_revisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quote_id", sa.Integer(), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("quote_version", sa.Integer(), nullable=False),
        sa.Column("source_request_version", sa.Integer(), nullable=False),
        sa.Column("status", quote_status, nullable=False),
        sa.Column("quote_number", sa.String(length=48), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("customer_name_snapshot", sa.String(length=160), nullable=False),
        sa.Column("contact_name_snapshot", sa.String(length=128), nullable=True),
        sa.Column("request_product_code", product_code, nullable=False),
        sa.Column("request_quantity", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default=sa.text("'KRW'")),
        sa.Column("total_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("formula_version", sa.String(length=64), nullable=False),
        sa.Column("rounding_policy_version", sa.String(length=64), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("line_count", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("revision_number > 0", name="ck_quote_revisions_positive_revision_number"),
        sa.CheckConstraint("quote_version > 0", name="ck_quote_revisions_positive_quote_version"),
        sa.CheckConstraint("request_quantity > 0", name="ck_quote_revisions_positive_request_quantity"),
        sa.CheckConstraint("source_request_version > 0", name="ck_quote_revisions_positive_source_request_version"),
        sa.CheckConstraint("line_count >= 0", name="ck_quote_revisions_nonnegative_line_count"),
        sa.CheckConstraint("total_amount >= 0", name="ck_quote_revisions_nonnegative_total_amount"),
        sa.CheckConstraint("currency = 'KRW'", name="ck_quote_revisions_currency_krw"),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("quote_id", "revision_number", name="uq_quote_revisions_quote_revision_number"),
    )
    op.create_index("ix_quote_revisions_created_at", "quote_revisions", ["created_at"])
    op.create_index("ix_quote_revisions_quote_id", "quote_revisions", ["quote_id"])

    op.create_table(
        "quote_revision_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quote_revision_id", sa.Integer(), nullable=False),
        sa.Column("source_quote_line_id", sa.Integer(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("product_code", product_code, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("line_total", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("options_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("position > 0", name="ck_quote_revision_lines_positive_position"),
        sa.CheckConstraint("quantity > 0", name="ck_quote_revision_lines_positive_quantity"),
        sa.CheckConstraint("unit_price >= 0", name="ck_quote_revision_lines_nonnegative_unit_price"),
        sa.CheckConstraint("line_total >= 0", name="ck_quote_revision_lines_nonnegative_line_total"),
        sa.ForeignKeyConstraint(["quote_revision_id"], ["quote_revisions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("quote_revision_id", "position", name="uq_quote_revision_lines_revision_position"),
    )
    op.create_index("ix_quote_revision_lines_quote_revision_id", "quote_revision_lines", ["quote_revision_id"])

    op.execute(
        """
        CREATE FUNCTION prevent_quote_revision_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'quote revisions are immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER quote_revisions_immutable
        BEFORE UPDATE OR DELETE ON quote_revisions
        FOR EACH ROW EXECUTE FUNCTION prevent_quote_revision_mutation();
        """
    )
    op.execute(
        """
        CREATE TRIGGER quote_revision_lines_immutable
        BEFORE UPDATE OR DELETE ON quote_revision_lines
        FOR EACH ROW EXECUTE FUNCTION prevent_quote_revision_mutation();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS quote_revision_lines_immutable ON quote_revision_lines")
    op.execute("DROP TRIGGER IF EXISTS quote_revisions_immutable ON quote_revisions")
    op.execute("DROP FUNCTION IF EXISTS prevent_quote_revision_mutation()")
    op.drop_table("quote_revision_lines")
    op.drop_table("quote_revisions")
    op.drop_table("quote_lines")
    op.drop_table("quotes")
    postgresql.ENUM(name="quote_status").drop(op.get_bind(), checkfirst=True)
