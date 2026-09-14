"""PullRequest Pydantic schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.repository import RepositoryRead


class PullRequestBase(BaseModel):
    github_pr_id: int
    number: int
    title: str
    description: str | None = None
    author_login: str
    base_sha: str
    head_sha: str
    state: str = "open"
    is_draft: bool = False


class PullRequestCreate(PullRequestBase):
    repository_id: str


class PullRequestUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    base_sha: str | None = None
    head_sha: str | None = None
    state: str | None = None
    is_draft: bool | None = None


class PullRequestRead(PullRequestBase):
    id: str
    repository_id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PullRequestDetail(PullRequestRead):
    repository: RepositoryRead | None = None
    latest_review_status: str | None = None
