"""Phase 7 Empirical Benchmarking schema

Revision ID: 006_phase7_benchmarking_tables
Revises: 005_phase5_mcp_governance_publishing
Create Date: 2026-09-14 17:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_phase7_benchmarking_tables"
down_revision: str | None = "005_phase5_mcp_governance_publishing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create benchmark_runs table
    op.create_table(
        "benchmark_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("dataset_version", sa.String(length=50), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="RUNNING"),
        sa.Column("git_revision", sa.String(length=64), nullable=True),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("metrics_summary", sa.JSON(), nullable=True),
        sa.Column("scenarios_total", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scenarios_passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scenarios_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_benchmark_runs_dataset_version", "benchmark_runs", ["dataset_version"])
    op.create_index("ix_benchmark_runs_status", "benchmark_runs", ["status"])

    # 2. Create benchmark_results table
    op.create_table(
        "benchmark_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("scenario_id", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("language", sa.String(length=50), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("scenario_type", sa.String(length=50), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("raw_findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("final_findings_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tp_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fp_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fn_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("raw_findings", sa.JSON(), nullable=False),
        sa.Column("final_findings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["run_id"], ["benchmark_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_benchmark_results_run_id", "benchmark_results", ["run_id"])
    op.create_index("ix_benchmark_results_scenario_id", "benchmark_results", ["scenario_id"])
    op.create_index("ix_benchmark_results_run_scenario", "benchmark_results", ["run_id", "scenario_id"])

    # 3. Create benchmark_finding_evaluations table
    op.create_table(
        "benchmark_finding_evaluations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("result_id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=100), nullable=False),
        sa.Column("classification", sa.String(length=50), nullable=False),
        sa.Column("predicted_category", sa.String(length=50), nullable=True),
        sa.Column("expected_category", sa.String(length=50), nullable=True),
        sa.Column("category_matched", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("predicted_severity", sa.String(length=50), nullable=True),
        sa.Column("expected_severity", sa.String(length=50), nullable=True),
        sa.Column("severity_matched", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("line_matched", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("semantic_similarity", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("reasons", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["result_id"], ["benchmark_results.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_benchmark_finding_evaluations_result_id", "benchmark_finding_evaluations", ["result_id"])


def downgrade() -> None:
    op.drop_table("benchmark_finding_evaluations")
    op.drop_table("benchmark_results")
    op.drop_table("benchmark_runs")
