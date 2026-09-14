"""MCP Tools initialization and default registry."""

from app.schemas.tools import (
    FindReferencesInput,
    GetDependenciesInput,
    GetFileInput,
    GetPullRequestDiffInput,
    GetPullRequestFilesInput,
    GetPullRequestInput,
    GetRepositoryInput,
    GetReviewEvidenceInput,
    GetReviewFindingsInput,
    GetSymbolInput,
    GetTestsInput,
    RunValidationInput,
    SubmitReviewInput,
    ToolRiskLevel,
)
from app.tools.read_tools import (
    handle_find_references,
    handle_get_dependencies,
    handle_get_file,
    handle_get_pull_request,
    handle_get_pull_request_diff,
    handle_get_pull_request_files,
    handle_get_repository,
    handle_get_review_evidence,
    handle_get_review_findings,
    handle_get_symbol,
    handle_get_tests,
)
from app.tools.registry import ToolDefinition, ToolRegistry
from app.tools.review_tools import handle_submit_review
from app.tools.validation_tools import handle_run_validation


def create_default_registry() -> ToolRegistry:
    reg = ToolRegistry()

    # Read-only tools
    reg.register(
        ToolDefinition("get_pull_request", "Fetch pull request metadata", GetPullRequestInput, ToolRiskLevel.READ_ONLY, handle_get_pull_request)
    )
    reg.register(
        ToolDefinition("get_pull_request_diff", "Fetch unified diff for pull request", GetPullRequestDiffInput, ToolRiskLevel.READ_ONLY, handle_get_pull_request_diff)
    )
    reg.register(
        ToolDefinition("get_pull_request_files", "List files modified in pull request", GetPullRequestFilesInput, ToolRiskLevel.READ_ONLY, handle_get_pull_request_files)
    )
    reg.register(
        ToolDefinition("get_repository", "Get repository information", GetRepositoryInput, ToolRiskLevel.READ_ONLY, handle_get_repository)
    )
    reg.register(
        ToolDefinition("get_file", "Get file contents at commit", GetFileInput, ToolRiskLevel.READ_ONLY, handle_get_file)
    )
    reg.register(
        ToolDefinition("get_symbol", "Get symbol declaration and line span", GetSymbolInput, ToolRiskLevel.READ_ONLY, handle_get_symbol)
    )
    reg.register(
        ToolDefinition("find_references", "Find references to symbol across repository", FindReferencesInput, ToolRiskLevel.READ_ONLY, handle_find_references)
    )
    reg.register(
        ToolDefinition("get_dependencies", "Get files that target file depends on", GetDependenciesInput, ToolRiskLevel.READ_ONLY, handle_get_dependencies)
    )
    reg.register(
        ToolDefinition("get_tests", "Get test files covering target file", GetTestsInput, ToolRiskLevel.READ_ONLY, handle_get_tests)
    )
    reg.register(
        ToolDefinition("get_review_findings", "Fetch findings generated for review job", GetReviewFindingsInput, ToolRiskLevel.READ_ONLY, handle_get_review_findings)
    )
    reg.register(
        ToolDefinition("get_review_evidence", "Fetch evidence items for finding", GetReviewEvidenceInput, ToolRiskLevel.READ_ONLY, handle_get_review_evidence)
    )

    # Operational tools
    reg.register(
        ToolDefinition("run_validation", "Execute test or static analysis scenario in sandbox", RunValidationInput, ToolRiskLevel.LOW_RISK, handle_run_validation)
    )
    reg.register(
        ToolDefinition("submit_review", "Publish atomic review and inline comments to GitHub", SubmitReviewInput, ToolRiskLevel.CONSEQUENTIAL, handle_submit_review, requires_approval=True)
    )

    return reg


default_registry = create_default_registry()

__all__ = ["ToolDefinition", "ToolRegistry", "create_default_registry", "default_registry"]
