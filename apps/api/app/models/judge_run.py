"""JudgeRun ORM model for storing Adversarial Judge execution records."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.judge_decision import JudgeDecisionModel
    from app.models.review_job import ReviewJob


class JudgeRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Execution record for an Adversarial Judge run on a review job."""

    __tablename__ = "judge_runs"

    review_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    prompt_version: Mapped[str] = mapped_column(
        String(50), default="judge.v1", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default="COMPLETED", index=True, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    latency_ms: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    input_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    output_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    total_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    estimated_cost: Mapped[float] = mapped_column(
        Numeric(10, 6), default=0.0, nullable=False
    )

    # Relationships
    review_job: Mapped["ReviewJob"] = relationship("ReviewJob")
    decisions: Mapped[list["JudgeDecisionModel"]] = relationship(
        "JudgeDecisionModel", back_populates="judge_run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_judge_runs_job_status", "review_job_id", "status"),
    )
