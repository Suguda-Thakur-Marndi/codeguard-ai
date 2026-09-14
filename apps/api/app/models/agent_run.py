"""AgentRun ORM model representing execution of an individual specialist review agent."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.agent_trace import AgentTrace
    from app.models.review_finding import ReviewFindingModel
    from app.models.review_job import ReviewJob


class AgentExecutionStatus(enum.StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    RETRYING = "RETRYING"


class AgentRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Execution record for an individual specialist agent during a review job."""

    __tablename__ = "agent_runs"

    review_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    agent_name: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )
    agent_version: Mapped[str] = mapped_column(
        String(20), default="1.0.0", nullable=False
    )
    model_name: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    prompt_version: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    status: Mapped[AgentExecutionStatus] = mapped_column(
        Enum(AgentExecutionStatus, name="agent_execution_status", native_enum=False),
        default=AgentExecutionStatus.PENDING,
        index=True,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
    latency_ms: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    retry_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # Relationships
    review_job: Mapped["ReviewJob"] = relationship(
        "ReviewJob", back_populates="agent_runs"
    )
    findings: Mapped[list["ReviewFindingModel"]] = relationship(
        "ReviewFindingModel", back_populates="agent_run"
    )
    traces: Mapped[list["AgentTrace"]] = relationship(
        "AgentTrace", back_populates="agent_run"
    )

    __table_args__ = (
        Index("ix_agent_runs_job_agent", "review_job_id", "agent_name"),
        Index("ix_agent_runs_job_status", "review_job_id", "status"),
    )
