"""Phase 4 adversarial verification and execution validation database schema

Revision ID: 004_phase4_adversarial_verification
Revises: 003_phase3_agentic_ai_review
Create Date: 2026-09-14 02:40:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004_phase4_adversarial_verification"
down_revision: str | None = "003_phase3_agentic_ai_review"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update review_findings with Phase 4 columns
    op.add_column("review_findings", sa.Column("original_severity", sa.String(length=50), nullable=True))
    op.add_column("review_findings", sa.Column("final_severity", sa.String(length=50), nullable=True))
    op.add_column("review_findings", sa.Column("specialist_confidence", sa.Float(), nullable=False, server_default="1.0"))
    op.add_column("review_findings", sa.Column("judge_confidence", sa.Float(), nullable=True))
    op.add_column("review_findings", sa.Column("final_confidence", sa.Float(), nullable=False, server_default="1.0"))
    op.add_column("review_findings", sa.Column("duplicate_of", sa.String(length=36), nullable=True))
    op.add_column("review_findings", sa.Column("root_cause_id", sa.String(length=36), nullable=True))
    op.add_column("review_findings", sa.Column("finding_group_id", sa.String(length=36), nullable=True))
    op.add_column("review_findings", sa.Column("source_agents", sa.JSON(), nullable=False, server_default="[]"))

    op.create_index("ix_review_findings_root_cause", "review_findings", ["root_cause_id"])
    op.create_index("ix_review_findings_duplicate_of", "review_findings", ["duplicate_of"])

    # 2. Create judge_runs table
    op.create_table(
        "judge_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("review_job_id", sa.String(length=36), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("prompt_version", sa.String(length=50), nullable=False, server_default="judge.v1"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="COMPLETED"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_cost", sa.Numeric(precision=10, scale=6), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["review_job_id"], ["review_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_judge_runs_review_job_id", "judge_runs", ["review_job_id"])
    op.create_index("ix_judge_runs_status", "judge_runs", ["status"])
    op.create_index("ix_judge_runs_job_status", "judge_runs", ["review_job_id", "status"])

    # 3. Create judge_decisions table
    op.create_table(
        "judge_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=False),
        sa.Column("judge_run_id", sa.String(length=36), nullable=False),
        sa.Column("decision", sa.String(length=50), nullable=False),
        sa.Column("final_severity", sa.String(length=50), nullable=False),
        sa.Column("final_confidence", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("boundary_passed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("factuality_passed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("actionability_passed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("severity_passed", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("duplicate_of", sa.String(length=36), nullable=True),
        sa.Column("root_cause_id", sa.String(length=36), nullable=True),
        sa.Column("verification_summary", sa.Text(), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["review_findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["judge_run_id"], ["judge_runs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_judge_decisions_finding_id", "judge_decisions", ["finding_id"])
    op.create_index("ix_judge_decisions_judge_run_id", "judge_decisions", ["judge_run_id"])
    op.create_index("ix_judge_decisions_decision", "judge_decisions", ["decision"])
    op.create_index("ix_judge_decisions_finding_run", "judge_decisions", ["finding_id", "judge_run_id"])

    # 4. Create validation_scenarios table
    op.create_table(
        "validation_scenarios",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=False),
        sa.Column("scenario_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("command", sa.String(length=500), nullable=False),
        sa.Column("environment", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("expected_behavior", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["review_findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_validation_scenarios_finding_id", "validation_scenarios", ["finding_id"])
    op.create_index("ix_validation_scenarios_type", "validation_scenarios", ["scenario_type"])
    op.create_index("ix_validation_scenarios_finding_type", "validation_scenarios", ["finding_id", "scenario_type"])

    # 5. Create validation_results table
    op.create_table(
        "validation_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("scenario_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("stdout_summary", sa.Text(), nullable=True),
        sa.Column("stderr_summary", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("evidence", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["validation_scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_validation_results_scenario_id", "validation_results", ["scenario_id"])
    op.create_index("ix_validation_results_status", "validation_results", ["status"])
    op.create_index("ix_validation_results_scenario_status", "validation_results", ["scenario_id", "status"])

    # 6. Create finding_evidence table
    op.create_table(
        "finding_evidence",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=False),
        sa.Column("evidence_type", sa.String(length=50), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("symbol_name", sa.String(length=255), nullable=True),
        sa.Column("snippet", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["review_findings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_finding_evidence_finding_id", "finding_evidence", ["finding_id"])
    op.create_index("ix_finding_evidence_type", "finding_evidence", ["evidence_type"])
    op.create_index("ix_finding_evidence_finding_type", "finding_evidence", ["finding_id", "evidence_type"])

    # 7. Create verification_events table
    op.create_table(
        "verification_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("review_job_id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["review_job_id"], ["review_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["finding_id"], ["review_findings.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verification_events_review_job_id", "verification_events", ["review_job_id"])
    op.create_index("ix_verification_events_finding_id", "verification_events", ["finding_id"])
    op.create_index("ix_verification_events_event_type", "verification_events", ["event_type"])
    op.create_index("ix_verification_events_job_type", "verification_events", ["review_job_id", "event_type"])


def downgrade() -> None:
    op.drop_table("verification_events")
    op.drop_table("finding_evidence")
    op.drop_table("validation_results")
    op.drop_table("validation_scenarios")
    op.drop_table("judge_decisions")
    op.drop_table("judge_runs")

    op.drop_index("ix_review_findings_duplicate_of", table_name="review_findings")
    op.drop_index("ix_review_findings_root_cause", table_name="review_findings")
    op.drop_column("review_findings", "source_agents")
    op.drop_column("review_findings", "finding_group_id")
    op.drop_column("review_findings", "root_cause_id")
    op.drop_column("review_findings", "duplicate_of")
    op.drop_column("review_findings", "final_confidence")
    op.drop_column("review_findings", "judge_confidence")
    op.drop_column("review_findings", "specialist_confidence")
    op.drop_column("review_findings", "final_severity")
    op.drop_column("review_findings", "original_severity")
