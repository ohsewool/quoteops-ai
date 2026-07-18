"""Create immutable grounded-copilot output artifacts.

Revision ID: 0007_copilot_output_domain
Revises: 0006_html_report_domain
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_copilot_output_domain"
down_revision = "0006_html_report_domain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "copilot_outputs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("quote_id", sa.Integer(), nullable=False),
        sa.Column("quote_revision_id", sa.Integer(), nullable=False),
        sa.Column("pricing_check_id", sa.Integer(), nullable=True),
        sa.Column("price_candidate_id", sa.Integer(), nullable=True),
        sa.Column("approval_request_id", sa.Integer(), nullable=True),
        sa.Column("report_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("generated_text", sa.Text(), nullable=False),
        sa.Column("grounding_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("source_artifacts_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("triggered_rules_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("deterministic_fallback", sa.Boolean(), nullable=False),
        sa.Column("generation_mode", sa.String(length=24), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=False),
        sa.Column("provider_model", sa.String(length=160), nullable=True),
        sa.Column("provider_metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("source_data_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(
            "purpose IN ('candidate_explanation', 'validation_summary', 'approval_reason_draft', "
            "'rejection_revision_suggestion', 'report_summary_draft')",
            name="ck_copilot_outputs_supported_purpose",
        ),
        sa.CheckConstraint("length(btrim(generated_text)) > 0", name="ck_copilot_outputs_nonblank_text"),
        sa.CheckConstraint("length(btrim(provider_name)) > 0", name="ck_copilot_outputs_nonblank_provider"),
        sa.CheckConstraint("length(btrim(generation_mode)) > 0", name="ck_copilot_outputs_nonblank_generation_mode"),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["quote_revision_id"], ["quote_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pricing_check_id"], ["pricing_checks.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["price_candidate_id"], ["price_candidates.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approval_request_id"], ["approval_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["report_id"], ["html_reports.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    for column in (
        "purpose",
        "quote_id",
        "quote_revision_id",
        "pricing_check_id",
        "price_candidate_id",
        "approval_request_id",
        "report_id",
        "created_by_user_id",
        "created_at",
    ):
        op.create_index(f"ix_copilot_outputs_{column}", "copilot_outputs", [column])

    op.execute(
        """
        CREATE FUNCTION enforce_copilot_output_lineage() RETURNS trigger AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM quote_revisions revision
                WHERE revision.id = NEW.quote_revision_id AND revision.quote_id = NEW.quote_id
            ) THEN
                RAISE EXCEPTION 'copilot output requires a matching quote revision';
            END IF;
            IF NEW.pricing_check_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM pricing_checks check_row
                WHERE check_row.id = NEW.pricing_check_id
                  AND check_row.quote_id = NEW.quote_id
                  AND check_row.quote_revision_id = NEW.quote_revision_id
            ) THEN
                RAISE EXCEPTION 'copilot pricing check must match quote revision';
            END IF;
            IF NEW.price_candidate_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM price_candidates candidate
                WHERE candidate.id = NEW.price_candidate_id AND candidate.pricing_check_id = NEW.pricing_check_id
            ) THEN
                RAISE EXCEPTION 'copilot candidate must match pricing check';
            END IF;
            IF NEW.report_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM html_reports report
                WHERE report.id = NEW.report_id
                  AND report.quote_id = NEW.quote_id
                  AND report.source_quote_revision_id = NEW.quote_revision_id
            ) THEN
                RAISE EXCEPTION 'copilot report must match quote revision';
            END IF;
            IF NEW.approval_request_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM approval_requests request
                LEFT JOIN approval_decisions decision ON decision.approval_request_id = request.id
                WHERE request.id = NEW.approval_request_id
                  AND request.quote_id = NEW.quote_id
                  AND (request.quote_revision_id = NEW.quote_revision_id OR decision.result_quote_revision_id = NEW.quote_revision_id)
            ) THEN
                RAISE EXCEPTION 'copilot approval must match quote revision';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE FUNCTION prevent_copilot_output_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'copilot outputs are immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        "CREATE TRIGGER copilot_outputs_lineage_guard BEFORE INSERT ON copilot_outputs "
        "FOR EACH ROW EXECUTE FUNCTION enforce_copilot_output_lineage();"
    )
    op.execute(
        "CREATE TRIGGER copilot_outputs_immutable BEFORE UPDATE OR DELETE ON copilot_outputs "
        "FOR EACH ROW EXECUTE FUNCTION prevent_copilot_output_mutation();"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS copilot_outputs_immutable ON copilot_outputs")
    op.execute("DROP TRIGGER IF EXISTS copilot_outputs_lineage_guard ON copilot_outputs")
    op.execute("DROP FUNCTION IF EXISTS prevent_copilot_output_mutation()")
    op.execute("DROP FUNCTION IF EXISTS enforce_copilot_output_lineage()")
    op.drop_table("copilot_outputs")
