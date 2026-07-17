"""Create deterministic pricing-check source and immutable evidence tables.

Revision ID: 0004_pricing_check_domain
Revises: 0003_quote_domain
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0004_pricing_check_domain"
down_revision = "0003_quote_domain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    product_code = postgresql.ENUM("a3_flyer", "brand_sticker", name="product_code", create_type=False)
    competitor_type = postgresql.ENUM(
        "local_shop",
        "similar_size",
        "premium_shop",
        "large_online",
        "ultra_low_cost",
        "unknown",
        name="competitor_type",
        create_type=False,
    )
    reference_price_basis = postgresql.ENUM(
        "unit_price", "total_price", name="reference_price_basis", create_type=False
    )
    pricing_check_status = postgresql.ENUM(
        "ready", "needs_review", "blocked", name="pricing_check_status", create_type=False
    )
    validation_status = postgresql.ENUM(
        "passed", "warning", "failed", name="validation_status", create_type=False
    )
    risk_level = postgresql.ENUM("low", "medium", "high", name="risk_level", create_type=False)
    validation_severity = postgresql.ENUM(
        "error", "warning", name="validation_severity", create_type=False
    )

    competitor_type.create(op.get_bind(), checkfirst=True)
    reference_price_basis.create(op.get_bind(), checkfirst=True)
    pricing_check_status.create(op.get_bind(), checkfirst=True)
    validation_status.create(op.get_bind(), checkfirst=True)
    risk_level.create(op.get_bind(), checkfirst=True)
    validation_severity.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", product_code, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("version > 0", name="ck_products_positive_version"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("code", name="uq_products_code"),
    )
    op.create_index("ix_products_code", "products", ["code"], unique=True)
    op.create_index("ix_products_active", "products", ["active"])
    op.create_index("ix_products_created_by_user_id", "products", ["created_by_user_id"])

    op.create_table(
        "cost_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("material_cost", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("labor_cost", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("overhead_cost", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("target_margin_rate", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("material_cost >= 0", name="ck_cost_profiles_nonnegative_material_cost"),
        sa.CheckConstraint("labor_cost >= 0", name="ck_cost_profiles_nonnegative_labor_cost"),
        sa.CheckConstraint("overhead_cost >= 0", name="ck_cost_profiles_nonnegative_overhead_cost"),
        sa.CheckConstraint("target_margin_rate >= 0 AND target_margin_rate < 1", name="ck_cost_profiles_valid_target_margin"),
        sa.CheckConstraint("version > 0", name="ck_cost_profiles_positive_version"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_cost_profiles_product_id", "cost_profiles", ["product_id"])
    op.create_index("ix_cost_profiles_active", "cost_profiles", ["active"])
    op.create_index("ix_cost_profiles_created_by_user_id", "cost_profiles", ["created_by_user_id"])
    op.create_index(
        "uq_cost_profiles_one_active_per_product",
        "cost_profiles",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("active"),
    )

    op.create_table(
        "competitors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("competitor_type", competitor_type, nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("version > 0", name="ck_competitors_positive_version"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_competitors_name", "competitors", ["name"])
    op.create_index("ix_competitors_competitor_type", "competitors", ["competitor_type"])
    op.create_index("ix_competitors_active", "competitors", ["active"])
    op.create_index("ix_competitors_created_by_user_id", "competitors", ["created_by_user_id"])

    op.create_table(
        "competitor_references",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("competitor_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price_basis", reference_price_basis, nullable=False),
        sa.Column("reference_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("source_note", sa.Text(), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("quantity > 0", name="ck_competitor_references_positive_quantity"),
        sa.CheckConstraint("reference_price >= 0", name="ck_competitor_references_nonnegative_price"),
        sa.ForeignKeyConstraint(["competitor_id"], ["competitors.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_competitor_references_competitor_id", "competitor_references", ["competitor_id"])
    op.create_index("ix_competitor_references_product_id", "competitor_references", ["product_id"])
    op.create_index("ix_competitor_references_observed_at", "competitor_references", ["observed_at"])
    op.create_index("ix_competitor_references_created_by_user_id", "competitor_references", ["created_by_user_id"])

    op.create_table(
        "pricing_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quote_id", sa.Integer(), nullable=False),
        sa.Column("quote_revision_id", sa.Integer(), nullable=False),
        sa.Column("quote_version", sa.Integer(), nullable=False),
        sa.Column("status", pricing_check_status, nullable=False),
        sa.Column("selected_strategy", sa.String(length=64), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default=sa.text("'KRW'")),
        sa.Column("total_cost", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("selected_total_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("selected_gross_profit", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("selected_margin_rate", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("minimum_margin_rate", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("formula_version", sa.String(length=64), nullable=False),
        sa.Column("validation_rule_version", sa.String(length=64), nullable=False),
        sa.Column("rounding_policy_version", sa.String(length=64), nullable=False),
        sa.Column("cost_snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("competitor_context_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("quote_version > 0", name="ck_pricing_checks_positive_quote_version"),
        sa.CheckConstraint("total_cost >= 0", name="ck_pricing_checks_nonnegative_total_cost"),
        sa.CheckConstraint("selected_total_price >= 0", name="ck_pricing_checks_nonnegative_selected_total_price"),
        sa.CheckConstraint("selected_gross_profit >= 0", name="ck_pricing_checks_nonnegative_selected_gross_profit"),
        sa.CheckConstraint("selected_margin_rate >= 0 AND selected_margin_rate < 1", name="ck_pricing_checks_valid_selected_margin"),
        sa.CheckConstraint("minimum_margin_rate >= 0 AND minimum_margin_rate < 1", name="ck_pricing_checks_valid_minimum_margin"),
        sa.CheckConstraint("currency = 'KRW'", name="ck_pricing_checks_currency_krw"),
        sa.CheckConstraint(
            "selected_strategy IN ('low_margin', 'target_margin', 'premium_margin')",
            name="ck_pricing_checks_supported_strategy",
        ),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["quote_revision_id"], ["quote_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_pricing_checks_quote_id", "pricing_checks", ["quote_id"])
    op.create_index("ix_pricing_checks_quote_revision_id", "pricing_checks", ["quote_revision_id"])
    op.create_index("ix_pricing_checks_status", "pricing_checks", ["status"])
    op.create_index("ix_pricing_checks_created_by_user_id", "pricing_checks", ["created_by_user_id"])
    op.create_index("ix_pricing_checks_created_at", "pricing_checks", ["created_at"])

    op.create_table(
        "price_candidates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pricing_check_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("strategy", sa.String(length=64), nullable=False),
        sa.Column("margin_rate", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("is_selected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("total_cost", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("estimated_gross_profit", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("estimated_margin_rate", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("notes_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("position > 0", name="ck_price_candidates_positive_position"),
        sa.CheckConstraint("margin_rate >= 0 AND margin_rate < 1", name="ck_price_candidates_valid_margin"),
        sa.CheckConstraint("total_cost >= 0", name="ck_price_candidates_nonnegative_total_cost"),
        sa.CheckConstraint("total_price >= 0", name="ck_price_candidates_nonnegative_total_price"),
        sa.CheckConstraint("estimated_gross_profit >= 0", name="ck_price_candidates_nonnegative_gross_profit"),
        sa.CheckConstraint("estimated_margin_rate >= 0 AND estimated_margin_rate < 1", name="ck_price_candidates_valid_estimated_margin"),
        sa.CheckConstraint(
            "strategy IN ('low_margin', 'target_margin', 'premium_margin')",
            name="ck_price_candidates_supported_strategy",
        ),
        sa.ForeignKeyConstraint(["pricing_check_id"], ["pricing_checks.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("pricing_check_id", "position", name="uq_price_candidates_check_position"),
    )
    op.create_index("ix_price_candidates_pricing_check_id", "price_candidates", ["pricing_check_id"])
    op.create_index(
        "uq_price_candidates_one_selected_per_check",
        "price_candidates",
        ["pricing_check_id"],
        unique=True,
        postgresql_where=sa.text("is_selected"),
    )

    op.create_table(
        "price_candidate_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("price_candidate_id", sa.Integer(), nullable=False),
        sa.Column("source_quote_revision_line_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("product_code", product_code, nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_cost", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("total_cost", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("calculation_inputs_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.CheckConstraint("position > 0", name="ck_price_candidate_lines_positive_position"),
        sa.CheckConstraint("quantity > 0", name="ck_price_candidate_lines_positive_quantity"),
        sa.CheckConstraint("unit_cost >= 0", name="ck_price_candidate_lines_nonnegative_unit_cost"),
        sa.CheckConstraint("unit_price >= 0", name="ck_price_candidate_lines_nonnegative_unit_price"),
        sa.CheckConstraint("total_cost >= 0", name="ck_price_candidate_lines_nonnegative_total_cost"),
        sa.CheckConstraint("total_price >= 0", name="ck_price_candidate_lines_nonnegative_total_price"),
        sa.ForeignKeyConstraint(["price_candidate_id"], ["price_candidates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_quote_revision_line_id"], ["quote_revision_lines.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("price_candidate_id", "position", name="uq_price_candidate_lines_candidate_position"),
    )
    op.create_index("ix_price_candidate_lines_price_candidate_id", "price_candidate_lines", ["price_candidate_id"])
    op.create_index("ix_price_candidate_lines_source_quote_revision_line_id", "price_candidate_lines", ["source_quote_revision_line_id"])

    op.create_table(
        "price_validation_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("price_candidate_id", sa.Integer(), nullable=False),
        sa.Column("validation_status", validation_status, nullable=False),
        sa.Column("risk_level", risk_level, nullable=False),
        sa.Column("minimum_margin_rate", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("minimum_margin_rate >= 0 AND minimum_margin_rate < 1", name="ck_price_validation_results_valid_minimum_margin"),
        sa.ForeignKeyConstraint(["price_candidate_id"], ["price_candidates.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("price_candidate_id", name="uq_price_validation_results_candidate"),
    )
    op.create_index("ix_price_validation_results_price_candidate_id", "price_validation_results", ["price_candidate_id"])
    op.create_index("ix_price_validation_results_validation_status", "price_validation_results", ["validation_status"])
    op.create_index("ix_price_validation_results_risk_level", "price_validation_results", ["risk_level"])

    op.create_table(
        "price_validation_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("price_validation_result_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=96), nullable=False),
        sa.Column("severity", validation_severity, nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("message", sa.String(length=280), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.ForeignKeyConstraint(["price_validation_result_id"], ["price_validation_results.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("price_validation_result_id", "code", name="uq_price_validation_checks_result_code"),
    )
    op.create_index("ix_price_validation_checks_price_validation_result_id", "price_validation_checks", ["price_validation_result_id"])

    op.execute(
        """
        CREATE FUNCTION prevent_pricing_evidence_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'pricing evidence is immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    for table, trigger in (
        ("pricing_checks", "pricing_checks_immutable"),
        ("price_candidates", "price_candidates_immutable"),
        ("price_candidate_lines", "price_candidate_lines_immutable"),
        ("price_validation_results", "price_validation_results_immutable"),
        ("price_validation_checks", "price_validation_checks_immutable"),
    ):
        op.execute(
            f"CREATE TRIGGER {trigger} BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION prevent_pricing_evidence_mutation();"
        )


def downgrade() -> None:
    for table, trigger in (
        ("price_validation_checks", "price_validation_checks_immutable"),
        ("price_validation_results", "price_validation_results_immutable"),
        ("price_candidate_lines", "price_candidate_lines_immutable"),
        ("price_candidates", "price_candidates_immutable"),
        ("pricing_checks", "pricing_checks_immutable"),
    ):
        op.execute(f"DROP TRIGGER IF EXISTS {trigger} ON {table}")
    op.execute("DROP FUNCTION IF EXISTS prevent_pricing_evidence_mutation()")
    op.drop_table("price_validation_checks")
    op.drop_table("price_validation_results")
    op.drop_table("price_candidate_lines")
    op.drop_table("price_candidates")
    op.drop_table("pricing_checks")
    op.drop_table("competitor_references")
    op.drop_table("competitors")
    op.drop_table("cost_profiles")
    op.drop_table("products")
    postgresql.ENUM(name="validation_severity").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="risk_level").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="validation_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="pricing_check_status").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="reference_price_basis").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="competitor_type").drop(op.get_bind(), checkfirst=True)
