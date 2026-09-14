"""CodeSymbol database repository."""

from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.code_symbol import CodeSymbol


class CodeSymbolRepository:
    """Database operations for CodeSymbol entities."""

    def __init__(self, db: Session):
        self.db = db

    def bulk_create(self, symbols: list[dict[str, Any]]) -> None:
        if not symbols:
            return
        objs = [CodeSymbol(**data) for data in symbols]
        self.db.add_all(objs)
        self.db.commit()

    def delete_by_repo_commit_and_files(
        self, repository_id: str, commit_sha: str, file_paths: list[str]
    ) -> int:
        if not file_paths:
            return 0
        stmt = delete(CodeSymbol).where(
            CodeSymbol.repository_id == repository_id,
            CodeSymbol.commit_sha == commit_sha,
            CodeSymbol.file_path.in_(file_paths),
        )
        res = self.db.execute(stmt)
        self.db.commit()
        return res.rowcount or 0

    def delete_all_for_commit(self, repository_id: str, commit_sha: str) -> int:
        stmt = delete(CodeSymbol).where(
            CodeSymbol.repository_id == repository_id,
            CodeSymbol.commit_sha == commit_sha,
        )
        res = self.db.execute(stmt)
        self.db.commit()
        return res.rowcount or 0

    def get_by_id(self, symbol_id: str) -> CodeSymbol | None:
        return self.db.get(CodeSymbol, symbol_id)

    def list_symbols(
        self,
        repository_id: str,
        commit_sha: str | None = None,
        file_path: str | None = None,
        kind: str | None = None,
        name_filter: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[CodeSymbol], int]:
        stmt = select(CodeSymbol).where(CodeSymbol.repository_id == repository_id)
        if commit_sha:
            stmt = stmt.where(CodeSymbol.commit_sha == commit_sha)
        if file_path:
            stmt = stmt.where(CodeSymbol.file_path == file_path)
        if kind:
            stmt = stmt.where(CodeSymbol.kind == kind.upper())
        if name_filter:
            stmt = stmt.where(CodeSymbol.name.ilike(f"%{name_filter}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = self.db.scalar(count_stmt) or 0

        stmt = stmt.order_by(CodeSymbol.file_path, CodeSymbol.start_line)
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        items = list(self.db.scalars(stmt).all())
        return items, total

    def get_by_file_path(
        self, repository_id: str, commit_sha: str, file_path: str
    ) -> list[CodeSymbol]:
        stmt = (
            select(CodeSymbol)
            .where(
                CodeSymbol.repository_id == repository_id,
                CodeSymbol.commit_sha == commit_sha,
                CodeSymbol.file_path == file_path,
            )
            .order_by(CodeSymbol.start_line)
        )
        return list(self.db.scalars(stmt).all())
