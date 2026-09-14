"""Tool risk classification and forbidden actions specification."""

import enum


class ToolRiskLevel(enum.StrEnum):
    READ_ONLY = "READ_ONLY"
    LOW_RISK = "LOW_RISK"
    CONSEQUENTIAL = "CONSEQUENTIAL"
    HIGH_RISK = "HIGH_RISK"


class PolicyDecision(enum.StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


FORBIDDEN_TOOL_ACTIONS = {
    "merge_pull_request": "Automatic PR merge is strictly forbidden in CodeGuard AI.",
    "branch_delete": "Automatic branch deletion is strictly forbidden.",
    "repository_delete": "Automatic repository deletion is strictly forbidden.",
    "repo_delete": "Automatic repository deletion is strictly forbidden.",
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
    "submit_review": ToolRiskLevel.CONSEQUENTIAL,
}


def classify_tool_risk(tool_name: str, parameters: dict | None = None) -> ToolRiskLevel:
    """Classifies a tool call risk level dynamically based on action and parameters."""
    if tool_name == "submit_review" and parameters and parameters.get("action") == "REQUEST_CHANGES":
        return ToolRiskLevel.HIGH_RISK
    return TOOL_RISK_MAP.get(tool_name, ToolRiskLevel.HIGH_RISK)


# Backward-compatible aliases
ToolRiskClassification = ToolRiskLevel
FORBIDDEN_OPERATIONS = FORBIDDEN_TOOL_ACTIONS

