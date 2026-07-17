"""Create immutable approved-Quote HTML report artifacts.

Revision ID: 0006_html_report_domain
Revises: 0005_approval_domain
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_html_report_domain"
down_revision = "0005_approval_domain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "html_reports",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("report_type", sa.String(length=48), nullable=False, server_default=sa.text("'approved_quote'")),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("quote_id", sa.Integer(), nullable=False),
        sa.Column("source_quote_revision_id", sa.Integer(), nullable=False),
        sa.Column("approval_request_id", sa.Integer(), nullable=False),
        sa.Column("approval_decision_id", sa.Integer(), nullable=False),
        sa.Column("predecessor_report_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column("html_content", sa.Text(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("report_type = 'approved_quote'", name="ck_html_reports_supported_type"),
        sa.CheckConstraint("length(btrim(title)) > 0", name="ck_html_reports_nonblank_title"),
        sa.CheckConstraint("length(btrim(summary_text)) > 0", name="ck_html_reports_nonblank_summary"),
        sa.CheckConstraint("length(html_content) > 0", name="ck_html_reports_nonempty_content"),
        sa.CheckConstraint("length(content_sha256) = 64", name="ck_html_reports_content_sha256"),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["source_quote_revision_id"], ["quote_revisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approval_request_id"], ["approval_requests.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["approval_decision_id"], ["approval_decisions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["predecessor_report_id"], ["html_reports.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    for column in (
        "quote_id",
        "source_quote_revision_id",
        "approval_request_id",
        "approval_decision_id",
        "predecessor_report_id",
        "created_by_user_id",
        "created_at",
    ):
        op.create_index(f"ix_html_reports_{column}", "html_reports", [column])

    op.execute(
        """
        CREATE FUNCTION enforce_html_report_lineage() RETURNS trigger AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM approval_requests request
                JOIN approval_decisions decision ON decision.approval_request_id = request.id
                JOIN quote_revisions revision ON revision.id = NEW.source_quote_revision_id
                WHERE request.id = NEW.approval_request_id
                  AND request.quote_id = NEW.quote_id
                  AND request.status = 'approved'::approval_status
                  AND decision.id = NEW.approval_decision_id
                  AND decision.decision = 'approved'::approval_status
                  AND decision.result_quote_revision_id = NEW.source_quote_revision_id
                  AND revision.quote_id = NEW.quote_id
                  AND revision.status = 'approved'::quote_status
            ) THEN
                RAISE EXCEPTION 'html report requires a matching approved quote revision and decision';
            END IF;
            IF NEW.predecessor_report_id IS NOT NULL AND NOT EXISTS (
                SELECT 1
                FROM html_reports predecessor
                WHERE predecessor.id = NEW.predecessor_report_id
                  AND predecessor.report_type = NEW.report_type
                  AND predecessor.quote_id = NEW.quote_id
                  AND predecessor.source_quote_revision_id = NEW.source_quote_revision_id
                  AND predecessor.approval_request_id = NEW.approval_request_id
                  AND predecessor.approval_decision_id = NEW.approval_decision_id
            ) THEN
                RAISE EXCEPTION 'html report predecessor must share the approved source lineage';
            END IF;
            IF position('content-security-policy' IN lower(NEW.html_content)) = 0 THEN
                RAISE EXCEPTION 'html report requires a content security policy';
            END IF;
            IF position('<script' IN lower(NEW.html_content)) > 0 THEN
                RAISE EXCEPTION 'html report must not contain executable script content';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE FUNCTION prevent_html_report_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'html reports are immutable';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        "CREATE TRIGGER html_reports_lineage_guard BEFORE INSERT ON html_reports "
        "FOR EACH ROW EXECUTE FUNCTION enforce_html_report_lineage();"
    )
    op.execute(
        "CREATE TRIGGER html_reports_immutable BEFORE UPDATE OR DELETE ON html_reports "
        "FOR EACH ROW EXECUTE FUNCTION prevent_html_report_mutation();"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS html_reports_immutable ON html_reports")
    op.execute("DROP TRIGGER IF EXISTS html_reports_lineage_guard ON html_reports")
    op.execute("DROP FUNCTION IF EXISTS prevent_html_report_mutation()")
    op.execute("DROP FUNCTION IF EXISTS enforce_html_report_lineage()")
    op.drop_table("html_reports")
