"""Require purpose-specific source context for copilot outputs.

Revision ID: 0008_copilot_context_guard
Revises: 0007_copilot_output_domain
Create Date: 2026-07-18
"""

from alembic import op


revision = "0008_copilot_context_guard"
down_revision = "0007_copilot_output_domain"
branch_labels = None
depends_on = None


PURPOSE_CONTEXT_CONSTRAINT = """
(purpose IN ('candidate_explanation', 'validation_summary', 'approval_reason_draft')
 AND pricing_check_id IS NOT NULL AND price_candidate_id IS NOT NULL)
OR (purpose = 'rejection_revision_suggestion' AND approval_request_id IS NOT NULL)
OR (purpose = 'report_summary_draft' AND report_id IS NOT NULL)
"""


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conrelid = 'copilot_outputs'::regclass
                  AND conname = 'ck_copilot_outputs_purpose_context'
            ) THEN
                ALTER TABLE copilot_outputs
                ADD CONSTRAINT ck_copilot_outputs_purpose_context
                CHECK ({PURPOSE_CONTEXT_CONSTRAINT});
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE copilot_outputs DROP CONSTRAINT IF EXISTS ck_copilot_outputs_purpose_context")
