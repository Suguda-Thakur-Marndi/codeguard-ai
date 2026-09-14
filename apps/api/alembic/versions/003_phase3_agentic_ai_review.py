"""Phase 3 agentic AI review engine database schema

Revision ID: 003_phase3_agentic_ai_review
Revises: 002_phase2_code_intelligence_tables
Create Date: 2026-09-14 02:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_phase3_agentic_ai_review"
down_revision: str | None = "002_phase2_code_intelligence_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update review_jobs with Phase 3 columns
    op.add_column(
        "review_jobs",
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "review_jobs",
        sa.Column("estimated_cost", sa.Numeric(precision=10, scale=6), nullable=False, server_default="0.0"),
    )
    op.add_column(
        "review_jobs",
        sa.Column(
            "agents_executed",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
            server_default="[]",
        ),
    )

    # 2. agent_runs table
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("review_job_id", sa.String(length=36), nullable=False),
        sa.Column("agent_name", sa.String(length=50), nullable=False),
        sa.Column("agent_version", sa.String(length=20), nullable=False, server_default="1.0.0"),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost", sa.Numeric(precision=10, scale=6), nullable=False, server_default="0.0"),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["review_job_id"], ["review_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_runs_review_job_id", "agent_runs", ["review_job_id"], unique=False)
    op.create_index("ix_agent_runs_agent_name", "agent_runs", ["agent_name"], unique=False)
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"], unique=False)
    op.create_index("ix_agent_runs_job_agent", "agent_runs", ["review_job_id", "agent_name"], unique=False)
    op.create_index("ix_agent_runs_job_status", "agent_runs", ["review_job_id", "status"], unique=False)

    # 3. review_findings table
    op.create_table(
        "review_findings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("review_job_id", sa.String(length=36), nullable=False),
        sa.Column("agent_run_id", sa.String(length=36), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False, server_default="RIGHT"),
        sa.Column("start_line", sa.Integer(), nullable=True),
        sa.Column("start_side", sa.String(length=10), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("impact", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("affected_symbol", sa.String(length=255), nullable=True),
        sa.Column(
            "related_files",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "related_symbols",
            postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"),
            nullable=False,
            server_default="[]",
        ),
        sa.Column("agent_name", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="CANDIDATE"),
        sa.Column("validation_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["review_job_id"], ["review_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_findings_review_job_id", "review_findings", ["review_job_id"], unique=False)
    op.create_index("ix_review_findings_file_path", "review_findings", ["file_path"], unique=False)
    op.create_index("ix_review_findings_category", "review_findings", ["category"], unique=False)
    op.create_index("ix_review_findings_severity", "review_findings", ["severity"], unique=False)
    op.create_index("ix_review_findings_status", "review_findings", ["status"], unique=False)
    op.create_index("ix_review_findings_job_severity", "review_findings", ["review_job_id", "severity"], unique=False)
    op.create_index("ix_review_findings_job_category", "review_findings", ["review_job_id", "category"], unique=False)
    op.create_index("ix_review_findings_job_status", "review_findings", ["review_job_id", "status"], unique=False)
    op.create_index("ix_review_findings_file_line", "review_findings", ["file_path", "line_number"], unique=False)

    # 4. agent_traces table
    op.create_table(
        "agent_traces",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("review_job_id", sa.String(length=36), nullable=False),
        sa.Column("agent_run_id", sa.String(length=36), nullable=True),
        sa.Column("node_name", sa.String(length=100), nullable=False),
        sa.Column("agent_name", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("model_name", sa.String(length=100), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["review_job_id"], ["review_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_traces_review_job_id", "agent_traces", ["review_job_id"], unique=False)
    op.create_index("ix_agent_traces_node_name", "agent_traces", ["node_name"], unique=False)
    op.create_index("ix_agent_traces_job_node", "agent_traces", ["review_job_id", "node_name"], unique=False)


def downgrade() -> None:
    op.drop_table("agent_traces")
    op.drop_table("review_findings")
    op.drop_table("agent_runs")
    op.drop_column("review_jobs", "agents_executed")
    op.drop_column("review_jobs", "estimated_cost")
    op.drop_column("review_jobs", "total_tokens")
