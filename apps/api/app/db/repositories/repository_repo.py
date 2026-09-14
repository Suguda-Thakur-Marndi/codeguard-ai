"""Repository repository implementation."""


from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.repositories.base_repo import BaseRepository
from app.models.repository import Repository


class RepositoryRepository(BaseRepository[Repository]):
    """Data access operations for Repository entities."""

    def __init__(self, db: Session):
        super().__init__(Repository, db)

    def get_by_github_repo_id(self, github_repo_id: int) -> Repository | None:
        """Look up repository by GitHub repository numeric ID."""
        stmt = select(Repository).where(Repository.github_repo_id == github_repo_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_full_name(self, full_name: str) -> Repository | None:
        """Look up repository by owner/name (e.g. 'octocat/Hello-World')."""
        stmt = select(Repository).where(Repository.full_name == full_name)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_repositories(
        self,
        page: int = 1,
        page_size: int = 20,
        organization_id: str | None = None,
    ) -> tuple[list[Repository], int]:
        """List repositories optionally filtered by organization."""
        filters = []
        if organization_id:
            filters.append(Repository.organization_id == organization_id)
        return self.get_all(
            page=page,
            page_size=page_size,
            filters=filters,
            order_by=Repository.full_name.asc(),
        )

    def get_or_create(
        self,
        organization_id: str,
        github_repo_id: int,
        owner: str,
        name: str,
        full_name: str,
        default_branch: str = "main",
        is_private: bool = True,
    ) -> Repository:
        """Find existing repository or create new one."""
        repo = self.get_by_github_repo_id(github_repo_id)
        if repo:
            updated = False
            if repo.full_name != full_name:
                repo.full_name = full_name
                repo.owner = owner
                repo.name = name
                updated = True
            if repo.default_branch != default_branch:
                repo.default_branch = default_branch
                updated = True
            if repo.is_private != is_private:
                repo.is_private = is_private
                updated = True
            if updated:
                self.update(repo)
            return repo

        new_repo = Repository(
            organization_id=organization_id,
            github_repo_id=github_repo_id,
            owner=owner,
            name=name,
            full_name=full_name,
            default_branch=default_branch,
            is_private=is_private,
        )
        return self.create(new_repo)
