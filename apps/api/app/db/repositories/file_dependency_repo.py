"""FileDependency database repository."""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.file_dependency import FileDependency


class FileDependencyRepository:
    """Database operations for FileDependency entities."""

    def __init__(self, db: Session):
        self.db = db

    def bulk_create(self, deps: list[dict[str, Any]]) -> None:
        if not deps:
            return
        objs = [FileDependency(**data) for data in deps]
        self.db.add_all(objs)
        self.db.commit()

    def delete_by_repo_commit_and_files(
        self, repository_id: str, commit_sha: str, file_paths: list[str]
    ) -> int:
        if not file_paths:
            return 0
        stmt = delete(FileDependency).where(
            FileDependency.repository_id == repository_id,
            FileDependency.commit_sha == commit_sha,
            FileDependency.source_file.in_(file_paths),
        )
        res = self.db.execute(stmt)
        self.db.commit()
        return res.rowcount or 0

    def delete_all_for_commit(self, repository_id: str, commit_sha: str) -> int:
        stmt = delete(FileDependency).where(
            FileDependency.repository_id == repository_id,
            FileDependency.commit_sha == commit_sha,
        )
        res = self.db.execute(stmt)
        self.db.commit()
        return res.rowcount or 0

    def get_dependencies_for_file(
        self, repository_id: str, commit_sha: str, source_file: str
    ) -> list[FileDependency]:
        stmt = select(FileDependency).where(
            FileDependency.repository_id == repository_id,
            FileDependency.commit_sha == commit_sha,
            FileDependency.source_file == source_file,
        )
        return list(self.db.scalars(stmt).all())

    def get_dependents_for_file(
        self, repository_id: str, commit_sha: str, target_file: str
    ) -> list[FileDependency]:
        stmt = select(FileDependency).where(
            FileDependency.repository_id == repository_id,
            FileDependency.commit_sha == commit_sha,
            FileDependency.target_file == target_file,
        )
        return list(self.db.scalars(stmt).all())
