"""FindingEvidence ORM model for storing immutable grounding evidence chains."""

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.review_finding import ReviewFindingModel


class FindingEvidenceModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable evidence record associated with a finding in the evidence chain."""

    __tablename__ = "finding_evidence"

    finding_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_findings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    evidence_type: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False  # DIFF, CODE, AST, CALLER, DEPENDENCY, TEST, STATIC_ANALYSIS, RUNTIME
    )
    file_path: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    line_start: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    line_end: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    symbol_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    snippet: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    source_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )

    # Relationships
    finding: Mapped["ReviewFindingModel"] = relationship(
        "ReviewFindingModel", back_populates="grounding_evidence"
    )

    __table_args__ = (
        Index("ix_finding_evidence_finding_type", "finding_id", "evidence_type"),
    )
