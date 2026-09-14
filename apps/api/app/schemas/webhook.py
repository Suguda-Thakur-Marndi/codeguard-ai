"""GitHub Webhook event Pydantic payload models."""

from pydantic import BaseModel


class GitHubUser(BaseModel):
    login: str
    id: int | None = None
    type: str | None = "User"


class GitHubRepoOwner(BaseModel):
    login: str
    id: int | None = None
    type: str | None = "Organization"


class GitHubRepoPayload(BaseModel):
    id: int
    name: str
    full_name: str
    owner: GitHubRepoOwner
    default_branch: str = "main"
    private: bool = True


class GitHubCommitRef(BaseModel):
    sha: str
    ref: str | None = None


class GitHubPullRequestPayload(BaseModel):
    id: int
    number: int
    title: str
    body: str | None = None
    user: GitHubUser
    base: GitHubCommitRef
    head: GitHubCommitRef
    state: str = "open"
    draft: bool = False


class GitHubInstallationPayload(BaseModel):
    id: int


class GitHubWebhookPayload(BaseModel):
    action: str | None = None
    number: int | None = None
    pull_request: GitHubPullRequestPayload | None = None
    repository: GitHubRepoPayload | None = None
    installation: GitHubInstallationPayload | None = None
    zen: str | None = None  # for ping event
    hook_id: int | None = None


class WebhookResponse(BaseModel):
    status: str
    event: str
    action: str | None = None
    review_job_id: str | None = None
    message: str | None = None
