"""SymbolReference ORM model representing cross-symbol and cross-file references."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.repository import Repository


class SymbolReference(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Represents a directional relationship/reference between symbols."""

    __tablename__ = "symbol_references"

    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(
        String(40), nullable=False, index=True
    )
    source_symbol: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    target_symbol: Mapped[str] = mapped_column(
        String(255), nullable=False, index=True
    )
    source_file: Mapped[str] = mapped_column(
        String(512), nullable=False, index=True
    )
    target_file: Mapped[str | None] = mapped_column(
        String(512), nullable=True, index=True
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reference_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True  # CALL, IMPORT, INHERITANCE, IMPLEMENTATION, etc.
    )
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        default=dict,
        nullable=False,
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository")

    __table_args__ = (
        Index("ix_symbol_refs_repo_commit", "repository_id", "commit_sha"),
        Index("ix_symbol_refs_repo_target", "repository_id", "target_symbol"),
    )
