"""Organization repository implementation."""


from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.repositories.base_repo import BaseRepository
from app.models.organization import Organization


class OrganizationRepository(BaseRepository[Organization]):
    """Data access operations for Organization entities."""

    def __init__(self, db: Session):
        super().__init__(Organization, db)

    def get_by_installation_id(self, installation_id: int) -> Organization | None:
        """Look up organization by its GitHub App installation ID."""
        stmt = select(Organization).where(Organization.github_installation_id == installation_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_or_create(
        self,
        installation_id: int,
        account_id: int,
        account_login: str,
        account_type: str = "Organization",
    ) -> Organization:
        """Find existing organization or create new one safely."""
        org = self.get_by_installation_id(installation_id)
        if org:
            # Update login if changed
            if org.github_account_login != account_login or org.account_type != account_type:
                org.github_account_login = account_login
                org.account_type = account_type
                self.update(org)
            return org

        new_org = Organization(
            github_installation_id=installation_id,
            github_account_id=account_id,
            github_account_login=account_login,
            account_type=account_type,
        )
        return self.create(new_org)
