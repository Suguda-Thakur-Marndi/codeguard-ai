"""Pydantic schemas for MCP Tool inputs, outputs, errors, and metadata."""

import enum
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ToolAction(enum.StrEnum):
    COMMENT = "COMMENT"
    REQUEST_CHANGES = "REQUEST_CHANGES"


class ToolRiskLevel(enum.StrEnum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    CONSEQUENTIAL = "CONSEQUENTIAL"
    HIGH_RISK = "HIGH_RISK"


class PolicyDecision(enum.StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


# ---------------------------------------------------------------------------
# Tool Input Schemas
# ---------------------------------------------------------------------------


class GetPullRequestInput(BaseModel):
    repository_id: str = Field(..., description="Internal repository UUID")
    pull_request_number: int = Field(..., ge=1, description="GitHub Pull Request number")


class GetPullRequestDiffInput(BaseModel):
    repository_id: str = Field(..., description="Internal repository UUID")
    pull_request_number: int = Field(..., ge=1, description="GitHub Pull Request number")


class GetPullRequestFilesInput(BaseModel):
    repository_id: str = Field(..., description="Internal repository UUID")
    pull_request_number: int = Field(..., ge=1, description="GitHub Pull Request number")


class GetRepositoryInput(BaseModel):
    repository_id: str = Field(..., description="Internal repository UUID")


class GetFileInput(BaseModel):
    repository_id: str = Field(..., description="Internal repository UUID")
    commit_sha: str = Field(..., min_length=7, max_length=40, description="Commit SHA")
    file_path: str = Field(..., description="Relative path to file in repo")


class GetSymbolInput(BaseModel):
    repository_id: str = Field(..., description="Internal repository UUID")
    commit_sha: str = Field(..., min_length=7, max_length=40, description="Commit SHA")
    symbol_name: str = Field(..., description="Fully qualified symbol name")


class FindReferencesInput(BaseModel):
    repository_id: str = Field(..., description="Internal repository UUID")
    commit_sha: str = Field(..., min_length=7, max_length=40, description="Commit SHA")
    symbol_name: str = Field(..., description="Target symbol name")


class GetDependenciesInput(BaseModel):
    repository_id: str = Field(..., description="Internal repository UUID")
    commit_sha: str = Field(..., min_length=7, max_length=40, description="Commit SHA")
    file_path: str = Field(..., description="Target file path")


class GetTestsInput(BaseModel):
    repository_id: str = Field(..., description="Internal repository UUID")
    commit_sha: str = Field(..., min_length=7, max_length=40, description="Commit SHA")
    target_file: str = Field(..., description="Source code file path to query associated tests for")


class GetReviewFindingsInput(BaseModel):
    review_job_id: str = Field(..., description="Review job UUID")


class GetReviewEvidenceInput(BaseModel):
    finding_id: str = Field(..., description="Finding UUID")


class RunValidationInput(BaseModel):
    review_job_id: str = Field(..., description="Review job UUID")
    finding_id: str = Field(..., description="Candidate finding UUID")
    scenario_id: str = Field(..., description="Validation scenario identifier")


class SubmitReviewInput(BaseModel):
    repository_id: str = Field(..., description="Internal repository UUID")
    pull_request_number: int = Field(..., ge=1, description="GitHub Pull Request number")
    head_sha: str = Field(..., min_length=7, max_length=40, description="Target PR HEAD SHA")
    review_job_id: str = Field(..., description="Review job UUID containing verified findings")
    action: Literal["COMMENT", "REQUEST_CHANGES"] = Field(
        default="COMMENT", description="Review action: COMMENT or REQUEST_CHANGES"
    )
    approval_id: str | None = Field(
        default=None, description="Approval request ID if action required human authorization"
    )


# ---------------------------------------------------------------------------
# Standard Envelopes & Error Models
# ---------------------------------------------------------------------------


class ToolMetadata(BaseModel):
    tool_name: str
    execution_id: str
    duration_ms: float


class ToolError(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class MCPResultEnvelope(BaseModel, Generic[T]):
    """Standardized tool output envelope across all MCP operations."""

    success: bool
    data: T | None = None
    error: ToolError | None = None
    metadata: ToolMetadata
