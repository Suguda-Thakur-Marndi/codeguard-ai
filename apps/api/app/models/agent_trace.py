"""AgentTrace ORM model for operational tracking and timeline inspection."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.agent_run import AgentRun
    from app.models.review_job import ReviewJob


class AgentTrace(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Execution step trace for operational observability without exposing private thought chains."""

    __tablename__ = "agent_traces"

    review_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    agent_run_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_runs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    node_name: Mapped[str] = mapped_column(
        String(100), index=True, nullable=False
    )
    agent_name: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    duration_ms: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    model_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
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
    retry_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # Relationships
    review_job: Mapped["ReviewJob"] = relationship(
        "ReviewJob", back_populates="traces"
    )
    agent_run: Mapped["AgentRun | None"] = relationship(
        "AgentRun", back_populates="traces"
    )

    __table_args__ = (
        Index("ix_agent_traces_job_node", "review_job_id", "node_name"),
    )
