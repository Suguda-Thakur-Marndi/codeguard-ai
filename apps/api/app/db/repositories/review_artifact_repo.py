"""ReviewArtifact repository implementation."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.repositories.base_repo import BaseRepository
from app.models.review_artifact import ArtifactType, ReviewArtifact


class ReviewArtifactRepository(BaseRepository[ReviewArtifact]):
    """Data access operations for ReviewArtifact entities."""

    def __init__(self, db: Session):
        super().__init__(ReviewArtifact, db)

    def get_by_job_and_type(
        self, review_job_id: str, artifact_type: ArtifactType
    ) -> ReviewArtifact | None:
        """Find artifact for a specific job and type."""
        stmt = select(ReviewArtifact).where(
            ReviewArtifact.review_job_id == review_job_id,
            ReviewArtifact.artifact_type == artifact_type,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def list_by_review_job(self, review_job_id: str) -> list[ReviewArtifact]:
        """Fetch all artifacts linked to a review job."""
        stmt = select(ReviewArtifact).where(
            ReviewArtifact.review_job_id == review_job_id
        ).order_by(ReviewArtifact.created_at.asc())
        return list(self.db.execute(stmt).scalars().all())

    def upsert_artifact(
        self,
        review_job_id: str,
        artifact_type: ArtifactType,
        content: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> ReviewArtifact:
        """Create or safely update artifact ensuring retry idempotency."""
        existing = self.get_by_job_and_type(review_job_id, artifact_type)
        if existing:
            existing.content = content
            existing.metadata_json = metadata_json or {}
            return self.update(existing)

        new_artifact = ReviewArtifact(
            review_job_id=review_job_id,
            artifact_type=artifact_type,
            content=content,
            metadata_json=metadata_json or {},
        )
        return self.create(new_artifact)
