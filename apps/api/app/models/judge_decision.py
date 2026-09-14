"""JudgeDecision ORM model for storing individual finding verification decisions."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.judge_run import JudgeRun
    from app.models.review_finding import ReviewFindingModel


class JudgeDecisionModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Adversarial Judge verification decision for a specific candidate finding."""

    __tablename__ = "judge_decisions"

    finding_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_findings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    judge_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("judge_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    decision: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False  # ACCEPT, REJECT, NEEDS_EXECUTION_VALIDATION
    )
    final_severity: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    final_confidence: Mapped[float] = mapped_column(
        Float, default=1.0, nullable=False
    )
    boundary_passed: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    factuality_passed: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    actionability_passed: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    severity_passed: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    duplicate_of: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    root_cause_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    verification_summary: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    rejection_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # Relationships
    finding: Mapped["ReviewFindingModel"] = relationship(
        "ReviewFindingModel", back_populates="judge_decisions"
    )
    judge_run: Mapped["JudgeRun"] = relationship(
        "JudgeRun", back_populates="decisions"
    )

    __table_args__ = (
        Index("ix_judge_decisions_finding_run", "finding_id", "judge_run_id"),
    )
