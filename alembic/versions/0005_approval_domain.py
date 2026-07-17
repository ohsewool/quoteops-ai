"""Create quote-scoped approval requests and immutable terminal decisions.

Revision ID: 0005_approval_domain
Revises: 0004_pricing_check_domain
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0005_approval_domain"
down_revision = "0004_pricing_check_domain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    approval_status = postgresql.ENUM(
        "pending", "approved", "rejected", "cancelled", name="approval_status", create_type=False
    )
    validation_status = postgresql.ENUM("passed", "warning", "failed", name="validation_status", create_type=False)
    risk_level = postgresql.ENUM("low", "medium", "high", name="risk_level", create_type=False)
    approval_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "approval_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quote_id", sa.Integer(), nullable=False),
        sa.Column("quote_revision_id", sa.Integer(), nullable=False),
        sa.Column("quote_version", sa.Integer(), nullable=False),
        sa.Column("pricing_check_id", sa.Integer(), nullable=False),
        sa.Column("price_candidate_id", sa.Integer(), nullable=False),
        sa.Column("requester_user_id", sa.Integer(), nullable=False),
        sa.Column("status", approval_status, nullable=False, server_default=sa.text("'pending'")),
        sa.Column("validation_status", validation_status, nullable=False),
        sa.Column("risk_level", risk_level, nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default=sa.text("'KRW'")),
        sa.Column("candidate_total_price", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("candidate_gross_profit", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("candidate_margin_rate", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("request_reason", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("quote_version > 0", name="ck_approval_requests_positive_quote_version"),
        sa.CheckConstraint("candidate_total_price >= 0", name="ck_approval_requests_nonnegative_candidate_price"),
        sa.CheckConstraint("candidate_gross_profit >= 0", name="ck_approval_requests_nonnegative_candidate_profit"),
        sa.CheckConstraint(
            "candidate_margin_rate >= 0 AND candidate_margin_rate < 1",
            name="ck_approval_requests_valid_candidate_margin",
        ),
        sa.CheckConstraint("currency = 'KRW'", name="ck_approval_requests_currency_krw"),
        sa.CheckConstraint("version > 0", name="ck_approval_requests_positive_version"),
        sa.CheckConstraint(
            "request_reason IS NULL OR length(btrim(request_reason)) > 0",
            name="ck_approval_requests_nonblank_request_reason",
        ),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["quote_revision_id"], ["quote_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pricing_check_id"], ["pricing_checks.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["price_candidate_id"], ["price_candidates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requester_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("pricing_check_id", "price_candidate_id", name="uq_approval_requests_pricing_candidate"),
    )
    for column in (
        "quote_id",
        "quote_revision_id",
        "pricing_check_id",
        "price_candidate_id",
        "requester_user_id",
        "status",
        "created_at",
    ):
        op.create_index(f"ix_approval_requests_{column}", "approval_requests", [column])

    op.create_table(
        "approval_decisions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("approval_request_id", sa.Integer(), nullable=False),
        sa.Column("decision", approval_status, nullable=False),
        sa.Column("reviewer_user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("result_quote_revision_id", sa.Integer(), nullable=False),
        sa.Column("demo_self_approval_used", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("decision IN ('approved', 'rejected')", name="ck_approval_decisions_terminal_decision"),
        sa.CheckConstraint(
            "decision <> 'rejected' OR length(btrim(reason)) > 0",
            name="ck_approval_decisions_rejection_reason",
        ),
        sa.ForeignKeyConstraint(["approval_request_id"], ["approval_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewer_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["result_quote_revision_id"], ["quote_revisions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("approval_request_id", name="uq_approval_decisions_request"),
    )
    for column in ("approval_request_id", "reviewer_user_id", "result_quote_revision_id", "created_at"):
        op.create_index(f"ix_approval_decisions_{column}", "approval_decisions", [column])

    op.execute(
        """
        CREATE FUNCTION enforce_approval_request_transition() RETURNS trigger AS $$
        BEGIN
            IF OLD.status <> 'pending'::approval_status THEN
                RAISE EXCEPTION 'approval request is terminal';
            END IF;
            IF NEW.status NOT IN ('approved'::approval_status, 'rejected'::approval_status, 'cancelled'::approval_status) THEN
                RAISE EXCEPTION 'approval request must move to a terminal state';
            END IF;
            IF NEW.version <> OLD.version + 1 THEN
                RAISE EXCEPTION 'approval request version must advance exactly once';
            END IF;
            IF NEW.quote_id IS DISTINCT FROM OLD.quote_id
               OR NEW.quote_revision_id IS DISTINCT FROM OLD.quote_revision_id
               OR NEW.quote_version IS DISTINCT FROM OLD.quote_version
               OR NEW.pricing_check_id IS DISTINCT FROM OLD.pricing_check_id
               OR NEW.price_candidate_id IS DISTINCT FROM OLD.price_candidate_id
               OR NEW.requester_user_id IS DISTINCT FROM OLD.requester_user_id
               OR NEW.validation_status IS DISTINCT FROM OLD.validation_status
               OR NEW.risk_level IS DISTINCT FROM OLD.risk_level
               OR NEW.currency IS DISTINCT FROM OLD.currency
               OR NEW.candidate_total_price IS DISTINCT FROM OLD.candidate_total_price
               OR NEW.candidate_gross_profit IS DISTINCT FROM OLD.candidate_gross_profit
               OR NEW.candidate_margin_rate IS DISTINCT FROM OLD.candidate_margin_rate
               OR NEW.request_reason IS DISTINCT FROM OLD.request_reason
               OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
                RAISE EXCEPTION 'approval request evidence is immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE FUNCTION prevent_approval_request_deletion() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'approval requests are immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE FUNCTION prevent_approval_decision_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'approval decisions are immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        "CREATE TRIGGER approval_requests_transition_guard BEFORE UPDATE ON approval_requests "
        "FOR EACH ROW EXECUTE FUNCTION enforce_approval_request_transition();"
    )
    op.execute(
        "CREATE TRIGGER approval_requests_immutable_delete BEFORE DELETE ON approval_requests "
        "FOR EACH ROW EXECUTE FUNCTION prevent_approval_request_deletion();"
    )
    op.execute(
        "CREATE TRIGGER approval_decisions_immutable BEFORE UPDATE OR DELETE ON approval_decisions "
        "FOR EACH ROW EXECUTE FUNCTION prevent_approval_decision_mutation();"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS approval_decisions_immutable ON approval_decisions")
    op.execute("DROP TRIGGER IF EXISTS approval_requests_immutable_delete ON approval_requests")
    op.execute("DROP TRIGGER IF EXISTS approval_requests_transition_guard ON approval_requests")
    op.execute("DROP FUNCTION IF EXISTS prevent_approval_decision_mutation()")
    op.execute("DROP FUNCTION IF EXISTS prevent_approval_request_deletion()")
    op.execute("DROP FUNCTION IF EXISTS enforce_approval_request_transition()")
    op.drop_table("approval_decisions")
    op.drop_table("approval_requests")
    postgresql.ENUM(name="approval_status").drop(op.get_bind(), checkfirst=True)
