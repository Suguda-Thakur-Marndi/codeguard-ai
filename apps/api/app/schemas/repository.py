"""Repository Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.organization import OrganizationRead


class RepositoryBase(BaseModel):
    github_repo_id: int
    owner: str
    name: str
    full_name: str
    default_branch: str = "main"
    is_private: bool = True


class RepositoryCreate(RepositoryBase):
    organization_id: str


class RepositoryRead(RepositoryBase):
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RepositoryDetail(RepositoryRead):
    organization: OrganizationRead | None = None
