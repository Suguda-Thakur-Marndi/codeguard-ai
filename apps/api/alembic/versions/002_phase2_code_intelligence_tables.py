"""Phase 2 code intelligence database schema

Revision ID: 002_phase2_code_intelligence_tables
Revises: 001_initial_phase1_tables
Create Date: 2026-09-14 01:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_phase2_code_intelligence_tables"
down_revision: str | None = "001_initial_phase1_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. repository_indexes table
    op.create_table(
        "repository_indexes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.String(length=36), nullable=False),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="NOT_INDEXED"),
        sa.Column("last_indexed_commit", sa.String(length=40), nullable=True),
        sa.Column("index_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("index_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("files_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_repository_indexes_repository_id", "repository_indexes", ["repository_id"], unique=False)
    op.create_index("ix_repository_indexes_commit_sha", "repository_indexes", ["commit_sha"], unique=False)
    op.create_index("ix_repository_indexes_status", "repository_indexes", ["status"], unique=False)
    op.create_index("ix_repository_indexes_repo_commit", "repository_indexes", ["repository_id", "commit_sha"], unique=True)
    op.create_index("ix_repository_indexes_repo_status", "repository_indexes", ["repository_id", "status"], unique=False)

    # 2. code_symbols table
    op.create_table(
        "code_symbols",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.String(length=36), nullable=False),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=50), nullable=False),
        sa.Column("language", sa.String(length=50), nullable=False),
        sa.Column("start_line", sa.Integer(), nullable=False),
        sa.Column("end_line", sa.Integer(), nullable=False),
        sa.Column("start_byte", sa.Integer(), nullable=True),
        sa.Column("end_byte", sa.Integer(), nullable=True),
        sa.Column("signature", sa.Text(), nullable=True),
        sa.Column("return_type", sa.String(length=255), nullable=True),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"), nullable=True),
        sa.Column("parent_symbol", sa.String(length=255), nullable=True),
        sa.Column("source_code", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_code_symbols_repository_id", "code_symbols", ["repository_id"], unique=False)
    op.create_index("ix_code_symbols_commit_sha", "code_symbols", ["commit_sha"], unique=False)
    op.create_index("ix_code_symbols_file_path", "code_symbols", ["file_path"], unique=False)
    op.create_index("ix_code_symbols_name", "code_symbols", ["name"], unique=False)
    op.create_index("ix_code_symbols_kind", "code_symbols", ["kind"], unique=False)
    op.create_index("ix_code_symbols_repo_commit_path", "code_symbols", ["repository_id", "commit_sha", "file_path"], unique=False)
    op.create_index("ix_code_symbols_repo_commit_name", "code_symbols", ["repository_id", "commit_sha", "name"], unique=False)

    # 3. symbol_references table
    op.create_table(
        "symbol_references",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.String(length=36), nullable=False),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.Column("source_symbol", sa.String(length=255), nullable=False),
        sa.Column("target_symbol", sa.String(length=255), nullable=False),
        sa.Column("source_file", sa.String(length=512), nullable=False),
        sa.Column("target_file", sa.String(length=512), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("reference_type", sa.String(length=50), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_symbol_refs_repository_id", "symbol_references", ["repository_id"], unique=False)
    op.create_index("ix_symbol_refs_commit_sha", "symbol_references", ["commit_sha"], unique=False)
    op.create_index("ix_symbol_refs_source_file", "symbol_references", ["source_file"], unique=False)
    op.create_index("ix_symbol_refs_target_file", "symbol_references", ["target_file"], unique=False)
    op.create_index("ix_symbol_refs_repo_commit", "symbol_references", ["repository_id", "commit_sha"], unique=False)
    op.create_index("ix_symbol_refs_repo_target", "symbol_references", ["repository_id", "target_symbol"], unique=False)

    # 4. file_dependencies table
    op.create_table(
        "file_dependencies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("repository_id", sa.String(length=36), nullable=False),
        sa.Column("commit_sha", sa.String(length=40), nullable=False),
        sa.Column("source_file", sa.String(length=512), nullable=False),
        sa.Column("target_file", sa.String(length=512), nullable=False),
        sa.Column("dependency_type", sa.String(length=50), nullable=False, server_default="IMPORTS"),
        sa.Column("imported_symbols", postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("line_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()).with_variant(sa.JSON(), "sqlite"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_file_deps_repository_id", "file_dependencies", ["repository_id"], unique=False)
    op.create_index("ix_file_deps_commit_sha", "file_dependencies", ["commit_sha"], unique=False)
    op.create_index("ix_file_deps_repo_commit", "file_dependencies", ["repository_id", "commit_sha"], unique=False)
    op.create_index("ix_file_deps_source", "file_dependencies", ["repository_id", "source_file"], unique=False)
    op.create_index("ix_file_deps_target", "file_dependencies", ["repository_id", "target_file"], unique=False)


def downgrade() -> None:
    op.drop_table("file_dependencies")
    op.drop_table("symbol_references")
    op.drop_table("code_symbols")
    op.drop_table("repository_indexes")
