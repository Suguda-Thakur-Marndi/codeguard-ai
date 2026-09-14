"""RepositoryIndex ORM model tracking repository AST indexing state and metrics."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.repository import Repository


class IndexStatus(enum.StrEnum):
    NOT_INDEXED = "NOT_INDEXED"
    INDEXING = "INDEXING"
    READY = "READY"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class RepositoryIndex(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Tracks indexing state, metadata, and performance for a repository commit."""

    __tablename__ = "repository_indexes"

    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True
    )
    status: Mapped[IndexStatus] = mapped_column(
        Enum(IndexStatus, name="index_status", native_enum=False),
        nullable=False,
        default=IndexStatus.NOT_INDEXED,
        index=True,
    )
    last_indexed_commit: Mapped[str | None] = mapped_column(String(40), nullable=True)
    index_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    index_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    files_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        default=dict,
        nullable=False,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository")

    __table_args__ = (
        Index("ix_repository_indexes_repo_commit", "repository_id", "commit_sha", unique=True),
        Index("ix_repository_indexes_repo_status", "repository_id", "status"),
    )
