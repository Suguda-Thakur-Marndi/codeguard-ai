"""GitHub Review Publication, Inline Comments, and Background Job models."""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.pull_request import PullRequest
    from app.models.repository import Repository
    from app.models.review_finding import ReviewFindingModel
    from app.models.review_job import ReviewJob


class PublicationStatus(enum.StrEnum):
    PENDING = "PENDING"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    STALE = "STALE"


class PublicationJobStatus(enum.StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STALE = "STALE"


class GitHubReviewPublication(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Record of an atomic GitHub Pull Request Review publication."""

    __tablename__ = "github_review_publications"

    review_job_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_jobs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    pull_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("pull_requests.id", ondelete="CASCADE"), index=True, nullable=False
    )
    head_sha: Mapped[str] = mapped_column(
        String(40), index=True, nullable=False
    )
    github_review_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    event: Mapped[str] = mapped_column(
        String(50), default="COMMENT", nullable=False
    )
    status: Mapped[PublicationStatus] = mapped_column(
        Enum(PublicationStatus, native_enum=False, length=50),
        default=PublicationStatus.PENDING,
        index=True,
        nullable=False,
    )
    comment_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    publication_key: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )

    # Relationships
    repository: Mapped["Repository"] = relationship("Repository")
    pull_request: Mapped["PullRequest"] = relationship("PullRequest")
    review_job: Mapped["ReviewJob"] = relationship("ReviewJob")
    comments: Mapped[list["GitHubReviewComment"]] = relationship(
        "GitHubReviewComment", back_populates="publication", cascade="all, delete-orphan"
    )
    jobs: Mapped[list["PublicationJob"]] = relationship(
        "PublicationJob", back_populates="publication", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("repository_id", "pull_request_id", "head_sha", "review_job_id", name="uq_repo_pr_sha_job_publication"),
        Index("ix_publications_job_status", "review_job_id", "status"),
    )


class GitHubReviewComment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Inline comment associated with an atomic GitHub review publication."""

    __tablename__ = "github_review_comments"

    publication_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("github_review_publications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    finding_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_findings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    github_comment_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )
    file_path: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    line_number: Mapped[int] = mapped_column(
        Integer, nullable=False
    )
    side: Mapped[str] = mapped_column(
        String(10), default="RIGHT", nullable=False
    )
    body: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(50), default="PUBLISHED", nullable=False
    )

    # Relationships
    publication: Mapped["GitHubReviewPublication"] = relationship("GitHubReviewPublication", back_populates="comments")
    finding: Mapped["ReviewFindingModel"] = relationship("ReviewFindingModel")


class PublicationJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Background execution job tracking for asynchronous review publishing."""

    __tablename__ = "publication_jobs"

    publication_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("github_review_publications.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[PublicationJobStatus] = mapped_column(
        Enum(PublicationJobStatus, native_enum=False, length=50),
        default=PublicationJobStatus.PENDING,
        index=True,
        nullable=False,
    )
    attempt: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer, default=3, nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

    # Relationships
    publication: Mapped["GitHubReviewPublication"] = relationship("GitHubReviewPublication", back_populates="jobs")
