"""FileDependency ORM model representing static file-to-file import relationships."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.repository import Repository


class FileDependency(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a static dependency (import) between two files."""

    __tablename__ = "file_dependencies"

    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True
    )
    source_file: Mapped[str] = mapped_column(
        String(512), nullable=False, index=True
    )
    target_file: Mapped[str] = mapped_column(
        String(512), nullable=False, index=True
    )
    dependency_type: Mapped[str] = mapped_column(
        String(50), nullable=False, default="IMPORTS"
    )
    imported_symbols: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        default=list,
        nullable=False,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        default=dict,
        nullable=False,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository")

    __table_args__ = (
        Index("ix_file_deps_repo_commit", "repository_id", "commit_sha"),
        Index("ix_file_deps_source", "repository_id", "source_file"),
        Index("ix_file_deps_target", "repository_id", "target_file"),
    )
