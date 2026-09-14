"""SymbolReference database repository."""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.symbol_reference import SymbolReference


class SymbolReferenceRepository:
    """Database operations for SymbolReference entities."""

    def __init__(self, db: Session):
        self.db = db

    def bulk_create(self, references: list[dict[str, Any]]) -> None:
        if not references:
            return
        objs = [SymbolReference(**data) for data in references]
        self.db.add_all(objs)
        self.db.commit()

    def delete_by_repo_commit_and_files(
        self, repository_id: str, commit_sha: str, file_paths: list[str]
    ) -> int:
        if not file_paths:
            return 0
        stmt = delete(SymbolReference).where(
            SymbolReference.repository_id == repository_id,
            SymbolReference.commit_sha == commit_sha,
            SymbolReference.source_file.in_(file_paths),
        )
        res = self.db.execute(stmt)
        self.db.commit()
        return res.rowcount or 0

    def delete_all_for_commit(self, repository_id: str, commit_sha: str) -> int:
        stmt = delete(SymbolReference).where(
            SymbolReference.repository_id == repository_id,
            SymbolReference.commit_sha == commit_sha,
        )
        res = self.db.execute(stmt)
        self.db.commit()
        return res.rowcount or 0

    def list_references(
        self,
        repository_id: str,
        commit_sha: str | None = None,
        target_symbol: str | None = None,
        source_file: str | None = None,
        target_file: str | None = None,
    ) -> list[SymbolReference]:
        stmt = select(SymbolReference).where(SymbolReference.repository_id == repository_id)
        if commit_sha:
            stmt = stmt.where(SymbolReference.commit_sha == commit_sha)
        if target_symbol:
            stmt = stmt.where(SymbolReference.target_symbol == target_symbol)
        if source_file:
            stmt = stmt.where(SymbolReference.source_file == source_file)
        if target_file:
            stmt = stmt.where(SymbolReference.target_file == target_file)

        return list(self.db.scalars(stmt).all())
