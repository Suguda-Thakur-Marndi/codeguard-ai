"""ReviewJob repository implementation."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.repositories.base_repo import BaseRepository
from app.models.review_job import ReviewJob, ReviewJobStatus


class ReviewJobRepository(BaseRepository[ReviewJob]):
    """Data access operations for ReviewJob entities."""

    def __init__(self, db: Session):
        super().__init__(ReviewJob, db)

    def get_active_job_for_pr(self, pull_request_id: str) -> ReviewJob | None:
        """Check if an active (PENDING or RUNNING) review job exists for this PR."""
        stmt = select(ReviewJob).where(
            ReviewJob.pull_request_id == pull_request_id,
            ReviewJob.status.in_([ReviewJobStatus.PENDING, ReviewJobStatus.RUNNING]),
        ).order_by(ReviewJob.created_at.desc())
        return self.db.execute(stmt).scalars().first()

    def list_by_pull_request(
        self,
        pull_request_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ReviewJob], int]:
        """List review jobs for a pull request in reverse chronological order."""
        return self.get_all(
            page=page,
            page_size=page_size,
            filters=[ReviewJob.pull_request_id == pull_request_id],
            order_by=ReviewJob.created_at.desc(),
        )

    def create_job(self, pull_request_id: str, trigger: str) -> ReviewJob:
        """Create new review job with PENDING status."""
        job = ReviewJob(
            pull_request_id=pull_request_id,
            status=ReviewJobStatus.PENDING,
            trigger=trigger,
        )
        return self.create(job)

    def mark_running(self, job_id: str) -> ReviewJob | None:
        """Transition job from PENDING to RUNNING with timestamp."""
        job = self.get_by_id(job_id)
        if not job:
            return None
        job.status = ReviewJobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        return self.update(job)

    def mark_completed(self, job_id: str) -> ReviewJob | None:
        """Transition job to COMPLETED with completion timestamp."""
        job = self.get_by_id(job_id)
        if not job:
            return None
        job.status = ReviewJobStatus.COMPLETED
        job.completed_at = datetime.now(UTC)
        job.error_message = None
        return self.update(job)

    def mark_failed(self, job_id: str, error_message: str) -> ReviewJob | None:
        """Transition job to FAILED with error message."""
        job = self.get_by_id(job_id)
        if not job:
            return None
        job.status = ReviewJobStatus.FAILED
        job.completed_at = datetime.now(UTC)
        job.error_message = error_message
        return self.update(job)
