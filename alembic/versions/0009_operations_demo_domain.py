"""Create V2-only operations demo guide state.

Revision ID: 0009_operations_demo_domain
Revises: 0008_copilot_context_guard
Create Date: 2026-07-18
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_operations_demo_domain"
down_revision = "0008_copilot_context_guard"
branch_labels = None
depends_on = None


def upgrade() -> None:
    status = sa.Enum("ready", "in_progress", "complete", name="demo_run_status")
    op.create_table(
        "demo_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_user_id", sa.Integer(), nullable=False),
        sa.Column("status", status, nullable=False, server_default=sa.text("'ready'")),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("artifacts_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("current_step >= 0", name="ck_demo_runs_nonnegative_current_step"),
        sa.CheckConstraint("current_step <= 6", name="ck_demo_runs_current_step_in_range"),
        sa.CheckConstraint("version > 0", name="ck_demo_runs_positive_version"),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    for column in ("owner_user_id", "status", "created_at"):
        op.create_index(f"ix_demo_runs_{column}", "demo_runs", [column])


def downgrade() -> None:
    op.drop_table("demo_runs")
    sa.Enum("ready", "in_progress", "complete", name="demo_run_status").drop(op.get_bind(), checkfirst=True)
