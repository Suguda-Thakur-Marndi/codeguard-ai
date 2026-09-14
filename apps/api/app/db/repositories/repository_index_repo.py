"""RepositoryIndex database repository."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.repository_index import IndexStatus, RepositoryIndex


class RepositoryIndexRepository:
    """Database repository for RepositoryIndex records."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_repo_and_commit(
        self, repository_id: str, commit_sha: str
    ) -> RepositoryIndex | None:
        stmt = select(RepositoryIndex).where(
            RepositoryIndex.repository_id == repository_id,
            RepositoryIndex.commit_sha == commit_sha,
        )
        return self.db.scalars(stmt).first()

    def get_latest_for_repo(self, repository_id: str) -> RepositoryIndex | None:
        stmt = (
            select(RepositoryIndex)
            .where(RepositoryIndex.repository_id == repository_id)
            .order_by(desc(RepositoryIndex.created_at))
        )
        return self.db.scalars(stmt).first()

    def upsert_index(
        self,
        repository_id: str,
        commit_sha: str,
        status: IndexStatus = IndexStatus.INDEXING,
        last_indexed_commit: str | None = None,
        files_processed: int = 0,
        files_failed: int = 0,
        error_count: int = 0,
        metadata_json: dict[str, Any] | None = None,
    ) -> RepositoryIndex:
        record = self.get_by_repo_and_commit(repository_id, commit_sha)
        now = datetime.now(UTC)
        if not record:
            record = RepositoryIndex(
                repository_id=repository_id,
                commit_sha=commit_sha,
                status=status,
                last_indexed_commit=last_indexed_commit,
                index_started_at=now,
                files_processed=files_processed,
                files_failed=files_failed,
                error_count=error_count,
                metadata_json=metadata_json or {},
            )
            self.db.add(record)
        else:
            record.status = status
            if last_indexed_commit:
                record.last_indexed_commit = last_indexed_commit
            record.files_processed = files_processed
            record.files_failed = files_failed
            record.error_count = error_count
            if metadata_json is not None:
                record.metadata_json = metadata_json
            if status in (IndexStatus.READY, IndexStatus.PARTIAL, IndexStatus.FAILED):
                record.index_completed_at = now

        self.db.commit()
        self.db.refresh(record)
        return record
