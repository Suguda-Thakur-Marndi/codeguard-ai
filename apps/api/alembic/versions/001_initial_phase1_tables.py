"""Initial Phase 1 database schema

Revision ID: 001_initial_phase1_tables
Revises:
Create Date: 2026-09-14 00:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial_phase1_tables"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("github_installation_id", sa.BigInteger(), nullable=False),
        sa.Column("github_account_id", sa.BigInteger(), nullable=False),
        sa.Column("github_account_login", sa.String(length=255), nullable=False),
        sa.Column("account_type", sa.String(length=50), nullable=False, server_default="Organization"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_organizations_github_installation_id", "organizations", ["github_installation_id"], unique=True)
    op.create_index("ix_organizations_github_account_login", "organizations", ["github_account_login"], unique=False)

    # 2. repositories table
    op.create_table(
        "repositories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("github_repo_id", sa.BigInteger(), nullable=False),
        sa.Column("owner", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=512), nullable=False),
        sa.Column("default_branch", sa.String(length=100), nullable=False, server_default="main"),
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repositories_organization_id", "repositories", ["organization_id"], unique=False)
    op.create_index("ix_repositories_github_repo_id", "repositories", ["github_repo_id"], unique=True)
    op.create_index("ix_repositories_full_name", "repositories", ["full_name"], unique=False)

    # 3. pull_requests table
    op.create_table(
        "pull_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.String(length=36), nullable=False),
        sa.Column("github_pr_id", sa.BigInteger(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("author_login", sa.String(length=255), nullable=False),
        sa.Column("base_sha", sa.String(length=40), nullable=False),
        sa.Column("head_sha", sa.String(length=40), nullable=False),
        sa.Column("state", sa.String(length=50), nullable=False, server_default="open"),
        sa.Column("is_draft", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pull_requests_repository_id", "pull_requests", ["repository_id"], unique=False)
    op.create_index("ix_pull_requests_github_pr_id", "pull_requests", ["github_pr_id"], unique=True)
    op.create_index("ix_pull_requests_state", "pull_requests", ["state"], unique=False)
    op.create_index("ix_pull_requests_repo_number", "pull_requests", ["repository_id", "number"], unique=False)

    # 4. review_jobs table
    op.create_table(
        "review_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("pull_request_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("trigger", sa.String(length=100), nullable=False, server_default="webhook:opened"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["pull_request_id"], ["pull_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_jobs_pull_request_id", "review_jobs", ["pull_request_id"], unique=False)
    op.create_index("ix_review_jobs_status", "review_jobs", ["status"], unique=False)
    op.create_index("ix_review_jobs_pr_status", "review_jobs", ["pull_request_id", "status"], unique=False)

    # 5. review_artifacts table
    op.create_table(
        "review_artifacts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("review_job_id", sa.String(length=36), nullable=False),
        sa.Column("artifact_type", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["review_job_id"], ["review_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_review_artifacts_review_job_id", "review_artifacts", ["review_job_id"], unique=False)
    op.create_index("ix_review_artifacts_artifact_type", "review_artifacts", ["artifact_type"], unique=False)
    op.create_index("ix_review_artifacts_job_type", "review_artifacts", ["review_job_id", "artifact_type"], unique=False)


def downgrade() -> None:
    op.drop_table("review_artifacts")
    op.drop_table("review_jobs")
    op.drop_table("pull_requests")
    op.drop_table("repositories")
    op.drop_table("organizations")
