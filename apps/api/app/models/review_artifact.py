"""ReviewArtifact ORM model."""

import enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.review_job import ReviewJob


class ArtifactType(enum.StrEnum):
    PR_METADATA = "PR_METADATA"
    DIFF = "DIFF"
    PARSED_DIFF = "PARSED_DIFF"
    DIFF_HUNKS = "DIFF_HUNKS"
    AST_CHUNKS = "AST_CHUNKS"
    CHANGED_LINE_INDEX = "CHANGED_LINE_INDEX"
    SYMBOL_INDEX = "SYMBOL_INDEX"
    REFERENCE_INDEX = "REFERENCE_INDEX"
    CONTEXT_MAP = "CONTEXT_MAP"
    PARSER_DIAGNOSTICS = "PARSER_DIAGNOSTICS"


class ReviewArtifact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Artifact produced during review job processing (e.g. metadata, raw diff)."""

    __tablename__ = "review_artifacts"

    review_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    artifact_type: Mapped[ArtifactType] = mapped_column(
        Enum(ArtifactType, name="artifact_type", native_enum=False),
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    # Cross-database JSON support (JSONB on PostgreSQL, JSON on SQLite)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"),
        default=dict,
        nullable=False,
    )

    # Relationship
    review_job: Mapped["ReviewJob"] = relationship(
        "ReviewJob", back_populates="artifacts"
    )

    __table_args__ = (
        Index("ix_review_artifacts_job_type", "review_job_id", "artifact_type"),
    )
