"""Tool risk classification and forbidden actions specification."""

from app.schemas.tools import ToolRiskLevel

FORBIDDEN_TOOL_ACTIONS = {
    "merge_pull_request": "Automatic PR merge is strictly forbidden in CodeGuard AI.",
    "branch_delete": "Automatic branch deletion is strictly forbidden.",
    "repository_delete": "Automatic repository deletion is strictly forbidden.",
    "secret_access": "Automatic secret or credential access is strictly forbidden.",
    "arbitrary_shell": "Arbitrary shell execution is strictly forbidden outside sandboxed validation.",
    "source_modify": "Direct source code modification is strictly forbidden.",
    "force_push": "Force push operations are strictly forbidden.",
    "admin_operations": "Arbitrary GitHub administrative operations are strictly forbidden.",
}

TOOL_RISK_MAP: dict[str, ToolRiskLevel] = {
    # Read-only tools
    "get_pull_request": ToolRiskLevel.READ_ONLY,
    "get_pull_request_diff": ToolRiskLevel.READ_ONLY,
    "get_pull_request_files": ToolRiskLevel.READ_ONLY,
    "get_repository": ToolRiskLevel.READ_ONLY,
    "get_file": ToolRiskLevel.READ_ONLY,
    "get_symbol": ToolRiskLevel.READ_ONLY,
    "find_references": ToolRiskLevel.READ_ONLY,
    "get_dependencies": ToolRiskLevel.READ_ONLY,
    "get_tests": ToolRiskLevel.READ_ONLY,
    "get_review_findings": ToolRiskLevel.READ_ONLY,
    "get_review_evidence": ToolRiskLevel.READ_ONLY,
    # Controlled operational tools
    "run_validation": ToolRiskLevel.LOW_RISK,
    "submit_review": ToolRiskLevel.CONSEQUENTIAL,  # Can escalate to HIGH_RISK for REQUEST_CHANGES
}
