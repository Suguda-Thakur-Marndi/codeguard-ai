"""ValidationScenario ORM model for storing execution or static verification scenarios."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.review_finding import ReviewFindingModel
    from app.models.validation_result import ValidationResultModel


class ValidationScenarioModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Validation scenario (behavioral test, structural check, or static analysis) for a finding."""

    __tablename__ = "validation_scenarios"

    finding_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_findings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    scenario_type: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False  # BEHAVIORAL, STRUCTURAL, STATIC
    )
    description: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    command: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    environment: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer, default=30, nullable=False
    )
    expected_behavior: Mapped[str] = mapped_column(
        Text, nullable=False
    )

    # Relationships
    finding: Mapped["ReviewFindingModel"] = relationship(
        "ReviewFindingModel", back_populates="validation_scenarios"
    )
    results: Mapped[list["ValidationResultModel"]] = relationship(
        "ValidationResultModel", back_populates="scenario", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_validation_scenarios_finding_type", "finding_id", "scenario_type"),
    )
