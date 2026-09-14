"""LangGraph typed agent state model for review orchestration."""

from typing import Any, TypedDict

from app.agents.schemas.comprehension import ComprehensionResult
from app.agents.schemas.finding import ReviewFinding


class ReviewAgentState(TypedDict, total=False):
    """Orchestrator state flowing through LangGraph review nodes."""

    # Review metadata & identifiers
    review_job_id: str
    repository_id: str
    pr_id: str
    base_sha: str
    head_sha: str
    pr_title: str
    pr_description: str

    # Code Intelligence inputs (Phase 2)
    changed_files: list[str]
    diff_hunks_by_file: dict[str, list[dict[str, Any]]]
    changed_lines_by_file: dict[str, dict[str, list[int]]]  # file -> {"RIGHT": [...], "LEFT": [...]}
    ast_chunks_by_file: dict[str, list[dict[str, Any]]]
    context_by_symbol: dict[str, dict[str, Any]]
    source_code_by_file: dict[str, str]

    # Comprehension & routing
    comprehension: ComprehensionResult | None
    selected_specialists: list[str]
    routing_reason: str

    # Specialist outputs
    security_findings: list[ReviewFinding]
    bug_findings: list[ReviewFinding]
    test_findings: list[ReviewFinding]
    performance_findings: list[ReviewFinding]

    # Aggregated findings
    raw_candidate_findings: list[ReviewFinding]
    validated_findings: list[ReviewFinding]
    invalid_findings: list[ReviewFinding]

    # Operational metrics & telemetry
    agent_runs: list[dict[str, Any]]
    agent_traces: list[dict[str, Any]]
    errors: list[dict[str, Any]]
    execution_status: str  # COMPLETED, PARTIAL, FAILED

    total_input_tokens: int
    total_output_tokens: int
    total_tokens: int
    estimated_cost: float
