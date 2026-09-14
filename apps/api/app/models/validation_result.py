"""ValidationResult ORM model for storing execution or static analysis outputs."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.validation_scenario import ValidationScenarioModel


class ValidationResultModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Captured result of executing a validation scenario in sandbox or static analyzer."""

    __tablename__ = "validation_results"

    scenario_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("validation_scenarios.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False  # PASS, FAIL, TIMEOUT, ERROR, SKIPPED
    )
    exit_code: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    stdout_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    stderr_summary: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    duration_ms: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )

    # Relationships
    scenario: Mapped["ValidationScenarioModel"] = relationship(
        "ValidationScenarioModel", back_populates="results"
    )

    __table_args__ = (
        Index("ix_validation_results_scenario_status", "scenario_id", "status"),
    )
