"""Benchmark ORM models for empirical evaluation tracking and reproducibility."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    pass


class BenchmarkRunModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persistent benchmark execution run."""

    __tablename__ = "benchmark_runs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_version: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="RUNNING", index=True)
    git_revision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    metrics_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    scenarios_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scenarios_passed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scenarios_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    results: Mapped[list["BenchmarkResultModel"]] = relationship(
        "BenchmarkResultModel",
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="BenchmarkResultModel.scenario_id",
    )


class BenchmarkResultModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Result of a single benchmark scenario execution."""

    __tablename__ = "benchmark_results"

    run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("benchmark_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scenario_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # PASSED, FAILED, ERROR
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    scenario_type: Mapped[str] = mapped_column(String(50), nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    raw_findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    final_findings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tp_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fp_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fn_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_findings: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    final_findings: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)

    run: Mapped["BenchmarkRunModel"] = relationship(
        "BenchmarkRunModel", back_populates="results"
    )
    evaluations: Mapped[list["BenchmarkFindingEvaluationModel"]] = relationship(
        "BenchmarkFindingEvaluationModel",
        back_populates="result",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_benchmark_results_run_scenario", "run_id", "scenario_id"),
    )


class BenchmarkFindingEvaluationModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Detailed evaluation record for an individual finding against ground truth."""

    __tablename__ = "benchmark_finding_evaluations"

    result_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("benchmark_results.id", ondelete="CASCADE"), index=True, nullable=False
    )
    finding_id: Mapped[str] = mapped_column(String(100), nullable=False)
    classification: Mapped[str] = mapped_column(String(50), nullable=False)  # TRUE_POSITIVE, FALSE_POSITIVE, FALSE_NEGATIVE
    predicted_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expected_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    category_matched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    predicted_severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    expected_severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    severity_matched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    line_matched: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    semantic_similarity: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    result: Mapped["BenchmarkResultModel"] = relationship(
        "BenchmarkResultModel", back_populates="evaluations"
    )
