"""Phase 5 MCP governance, human approval, and GitHub publishing schema

Revision ID: 005_phase5_mcp_governance_publishing
Revises: 004_phase4_adversarial_verification
Create Date: 2026-09-14 05:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_phase5_mcp_governance_publishing"
down_revision: str | None = "004_phase4_adversarial_verification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create approval_requests table
    op.create_table(
        "approval_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.String(length=36), nullable=False),
        sa.Column("pull_request_id", sa.String(length=36), nullable=False),
        sa.Column("review_job_id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=True),
        sa.Column("requested_action", sa.String(length=50), nullable=False, server_default="COMMENT"),
        sa.Column("risk_level", sa.String(length=50), nullable=False, server_default="CONSEQUENTIAL"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("requested_by", sa.String(length=100), nullable=False, server_default="agent"),
        sa.Column("approved_by", sa.String(length=100), nullable=True),
        sa.Column("head_sha", sa.String(length=40), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["review_findings.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pull_request_id"], ["pull_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_job_id"], ["review_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_requests_org", "approval_requests", ["organization_id"])
    op.create_index("ix_approval_requests_repo", "approval_requests", ["repository_id"])
    op.create_index("ix_approval_requests_pr", "approval_requests", ["pull_request_id"])
    op.create_index("ix_approval_requests_job", "approval_requests", ["review_job_id"])
    op.create_index("ix_approval_requests_status", "approval_requests", ["status"])
    op.create_index("ix_approval_requests_head_sha", "approval_requests", ["head_sha"])
    op.create_index("ix_approval_requests_pr_status", "approval_requests", ["pull_request_id", "status"])
    op.create_index("ix_approval_requests_job_sha", "approval_requests", ["review_job_id", "head_sha"])

    # 2. Create github_review_publications table
    op.create_table(
        "github_review_publications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("review_job_id", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.String(length=36), nullable=False),
        sa.Column("pull_request_id", sa.String(length=36), nullable=False),
        sa.Column("head_sha", sa.String(length=40), nullable=False),
        sa.Column("github_review_id", sa.BigInteger(), nullable=True),
        sa.Column("event", sa.String(length=50), nullable=False, server_default="COMMENT"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("comment_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("publication_key", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["pull_request_id"], ["pull_requests.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["review_job_id"], ["review_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("publication_key"),
        sa.UniqueConstraint("repository_id", "pull_request_id", "head_sha", "review_job_id", name="uq_repo_pr_sha_job_publication"),
    )
    op.create_index("ix_publications_job_id", "github_review_publications", ["review_job_id"])
    op.create_index("ix_publications_repo_id", "github_review_publications", ["repository_id"])
    op.create_index("ix_publications_pr_id", "github_review_publications", ["pull_request_id"])
    op.create_index("ix_publications_status", "github_review_publications", ["status"])
    op.create_index("ix_publications_head_sha", "github_review_publications", ["head_sha"])
    op.create_index("ix_publications_job_status", "github_review_publications", ["review_job_id", "status"])

    # 3. Create github_review_comments table
    op.create_table(
        "github_review_comments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("publication_id", sa.String(length=36), nullable=False),
        sa.Column("finding_id", sa.String(length=36), nullable=False),
        sa.Column("github_comment_id", sa.BigInteger(), nullable=True),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("side", sa.String(length=10), nullable=False, server_default="RIGHT"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PUBLISHED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["finding_id"], ["review_findings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["publication_id"], ["github_review_publications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_comments_pub_id", "github_review_comments", ["publication_id"])
    op.create_index("ix_review_comments_finding_id", "github_review_comments", ["finding_id"])

    # 4. Create publication_jobs table
    op.create_table(
        "publication_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("publication_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["publication_id"], ["github_review_publications.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pub_jobs_pub_id", "publication_jobs", ["publication_id"])
    op.create_index("ix_pub_jobs_status", "publication_jobs", ["status"])

    # 5. Create tool_execution_audit table
    op.create_table(
        "tool_execution_audit",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("principal_id", sa.String(length=100), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.String(length=36), nullable=True),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("risk_level", sa.String(length=50), nullable=False),
        sa.Column("authorization_decision", sa.String(length=50), nullable=False),
        sa.Column("approval_id", sa.String(length=36), nullable=True),
        sa.Column("execution_status", sa.String(length=50), nullable=False, server_default="SUCCESS"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tool_audit_principal", "tool_execution_audit", ["principal_id"])
    op.create_index("ix_tool_audit_org_id", "tool_execution_audit", ["organization_id"])
    op.create_index("ix_tool_audit_repo_id", "tool_execution_audit", ["repository_id"])
    op.create_index("ix_tool_audit_tool", "tool_execution_audit", ["tool_name"])
    op.create_index("ix_tool_audit_status", "tool_execution_audit", ["execution_status"])
    op.create_index("ix_tool_audit_org_tool", "tool_execution_audit", ["organization_id", "tool_name"])
    op.create_index("ix_tool_audit_created_at", "tool_execution_audit", ["created_at"])

    # 6. Create organization_review_policies table
    op.create_table(
        "organization_review_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("auto_publish_advisory", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("auto_publish_low", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("require_approval_for_high", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("require_approval_for_critical", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("allow_request_changes", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("allow_ai_github_comments", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("approval_expiry_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id"),
    )
    op.create_index("ix_org_policies_org_id", "organization_review_policies", ["organization_id"])


def downgrade() -> None:
    op.drop_table("organization_review_policies")
    op.drop_table("tool_execution_audit")
    op.drop_table("publication_jobs")
    op.drop_table("github_review_comments")
    op.drop_table("github_review_publications")
    op.drop_table("approval_requests")
