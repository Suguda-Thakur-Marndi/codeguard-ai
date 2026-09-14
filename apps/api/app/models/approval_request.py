"""ApprovalRequest ORM model for Human Approval governance."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.pull_request import PullRequest
    from app.models.repository import Repository
    from app.models.review_finding import ReviewFindingModel
    from app.models.review_job import ReviewJob


class ApprovalStatus(enum.StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ApprovalRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Approval request bound to a specific repository, PR, head SHA, finding and action."""

    __tablename__ = "approval_requests"

    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    pull_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pull_requests.id", ondelete="CASCADE"), index=True, nullable=False
    )
    review_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    finding_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("review_findings.id", ondelete="SET NULL"), index=True, nullable=True
    )
    requested_action: Mapped[str] = mapped_column(
        String(50), default="COMMENT", nullable=False
    )
    risk_level: Mapped[str] = mapped_column(
        String(50), default="CONSEQUENTIAL", nullable=False
    )
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, native_enum=False, length=50),
        default=ApprovalStatus.PENDING,
        index=True,
        nullable=False,
    )
    requested_by: Mapped[str] = mapped_column(
        String(100), default="agent", nullable=False
    )
    approved_by: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    head_sha: Mapped[str] = mapped_column(
        String(40), index=True, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    reason: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization")
    repository: Mapped["Repository"] = relationship("Repository")
    pull_request: Mapped["PullRequest"] = relationship("PullRequest")
    review_job: Mapped["ReviewJob"] = relationship("ReviewJob")
    finding: Mapped["ReviewFindingModel | None"] = relationship("ReviewFindingModel")

    __table_args__ = (
        Index("ix_approval_requests_pr_status", "pull_request_id", "status"),
        Index("ix_approval_requests_job_sha", "review_job_id", "head_sha"),
    )
