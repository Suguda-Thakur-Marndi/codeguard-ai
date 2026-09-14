"""CodeSymbol ORM model representing extracted functions, methods, classes, and types."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.repository import Repository


class CodeSymbol(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a code symbol extracted from AST parsing."""

    __tablename__ = "code_symbols"

    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True
    )
    file_path: Mapped[str] = mapped_column(
        String(512), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True  # FUNCTION, METHOD, CLASS, INTERFACE, TYPE, etc.
    )
    language: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    start_byte: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_byte: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signature: Mapped[str | None] = mapped_column(Text, nullable=True)
    return_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    parameters: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        nullable=True,
    )
    parent_symbol: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        default=dict,
        nullable=False,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository")

    __table_args__ = (
        Index("ix_code_symbols_repo_commit_path", "repository_id", "commit_sha", "file_path"),
        Index("ix_code_symbols_repo_commit_name", "repository_id", "commit_sha", "name"),
    )
