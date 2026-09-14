"""ReviewJob ORM model."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.agent_run import AgentRun
    from app.models.agent_trace import AgentTrace
    from app.models.pull_request import PullRequest
    from app.models.review_artifact import ReviewArtifact
    from app.models.review_finding import ReviewFindingModel


class ReviewJobStatus(enum.StrEnum):
    PENDING = "PENDING"
    PREPARING = "PREPARING"
    COMPREHENDING = "COMPREHENDING"
    ANALYZING = "ANALYZING"
    VALIDATING = "VALIDATING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ReviewJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Background review job lifecycle for a Pull Request."""

    __tablename__ = "review_jobs"

    pull_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pull_requests.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[ReviewJobStatus] = mapped_column(
        Enum(ReviewJobStatus, name="review_job_status", native_enum=False),
        default=ReviewJobStatus.PENDING,
        index=True,
        nullable=False,
    )
    trigger: Mapped[str] = mapped_column(
        String(100), default="webhook:opened", nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # Phase 3: Token, Cost, and Agent Execution tracking
    total_tokens: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    estimated_cost: Mapped[float] = mapped_column(
        Numeric(10, 6), default=0.0, nullable=False
    )
    agents_executed: Mapped[list[str]] = mapped_column(
        JSON, default=list, nullable=False
    )

    # Relationships
    pull_request: Mapped["PullRequest"] = relationship(
        "PullRequest", back_populates="review_jobs"
    )
    artifacts: Mapped[list["ReviewArtifact"]] = relationship(
        "ReviewArtifact", back_populates="review_job", cascade="all, delete-orphan", order_by="desc(ReviewArtifact.created_at)"
    )
    agent_runs: Mapped[list["AgentRun"]] = relationship(
        "AgentRun", back_populates="review_job", cascade="all, delete-orphan", order_by="AgentRun.started_at"
    )
    findings: Mapped[list["ReviewFindingModel"]] = relationship(
        "ReviewFindingModel", back_populates="review_job", cascade="all, delete-orphan", order_by="ReviewFindingModel.created_at"
    )
    traces: Mapped[list["AgentTrace"]] = relationship(
        "AgentTrace", back_populates="review_job", cascade="all, delete-orphan", order_by="AgentTrace.start_time"
    )

    __table_args__ = (
        Index("ix_review_jobs_pr_status", "pull_request_id", "status"),
    )
