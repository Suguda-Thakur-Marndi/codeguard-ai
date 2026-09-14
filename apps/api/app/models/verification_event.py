"""VerificationEvent ORM model for immutable audit trail of verification steps."""

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.review_finding import ReviewFindingModel
    from app.models.review_job import ReviewJob


class VerificationEventModel(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable audit trail log of verification lifecycle events."""

    __tablename__ = "verification_events"

    review_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    finding_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("review_findings.id", ondelete="SET NULL"), index=True, nullable=True
    )
    event_type: Mapped[str] = mapped_column(
        String(100), index=True, nullable=False
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )

    # Relationships
    review_job: Mapped["ReviewJob"] = relationship("ReviewJob")
    finding: Mapped["ReviewFindingModel | None"] = relationship("ReviewFindingModel")

    __table_args__ = (
        Index("ix_verification_events_job_type", "review_job_id", "event_type"),
    )
