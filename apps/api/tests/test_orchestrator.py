"""Tests for LangGraph ReviewWorkflowBuilder, parallel execution, failure isolation, and cost tracking."""

import pytest

from app.agents.llm.mock import MockLLMProvider
from app.agents.orchestrator.graph import ReviewWorkflowBuilder
from app.agents.schemas.comprehension import ComprehensionResult
from app.agents.schemas.finding import (
    EvidenceItem,
    EvidenceType,
    FindingCategory,
    FindingSeverity,
    FindingStatus,
    ReviewFinding,
    SpecialistFindingsOutput,
)


def create_initial_state(
    files: list[str] | None = None,
    changed_lines: dict | None = None,
) -> dict:
    f_list = files if files is not None else ["src/payment.py"]
    lines = changed_lines if changed_lines is not None else {"src/payment.py": {"RIGHT": [10, 11, 12], "LEFT": []}}
    return {
        "review_job_id": "job-12345",
        "repository_id": "repo-987",
        "pr_id": "pr-42",
        "pr_title": "Fix invoice charge calculation",
        "pr_description": "Updates tax calculation and discount logic.",
        "base_sha": "1111111111111111111111111111111111111111",
        "head_sha": "2222222222222222222222222222222222222222",
        "changed_files": f_list,
        "changed_lines_by_file": lines,
        "diff_hunks_by_file": {
            "src/payment.py": [
                {
                    "old_start": 10,
                    "old_lines": 3,
                    "new_start": 10,
                    "new_lines": 3,
                    "lines": [
                        {"line_type": "context", "content": "def calculate():"},
                        {"line_type": "added", "content": "    return amount * 1.1"},
                    ],
                }
            ]
        },
        "ast_chunks_by_file": {
            "src/payment.py": [
                {
                    "symbol_name": "calculate",
                    "node_type": "function_definition",
                    "start_line": 10,
                    "end_line": 12,
                    "code_snippet": "def calculate(): return amount * 1.1",
                }
            ]
        },
        "source_code_by_file": {"src/payment.py": "def calculate(): return amount * 1.1\n"},
        "context_by_symbol": {
            "calculate": {
                "direct_callers": ["checkout_view"],
                "direct_dependencies": ["TaxService"],
            }
        },
        "candidate_findings": [],
        "valid_findings": [],
        "invalid_findings": [],
        "errors": [],
        "agent_runs": [],
        "agent_traces": [],
        "total_tokens": 0,
        "estimated_cost": 0.0,
        "execution_status": "PREPARING",
        "execution_latencies": {},
    }


@pytest.mark.asyncio
async def test_langgraph_review_workflow_success():
    """LangGraph review workflow should execute comprehension, route to specialists, and validate findings."""
    provider = MockLLMProvider()

    # Comprehension Output
    comprehension_out = ComprehensionResult(
        intent="Update tax calculations",
        summary="Adjusts invoice tax multipliers.",
        functional_changes=["Changed tax rate multiplier to 1.1"],
        refactors=[],
        changed_components=["payment"],
        affected_interfaces=[],
        risk_areas=[],
        relevant_symbols=["calculate"],
    )
    provider.register_structured_response(
        lambda prompt, schema: schema is ComprehensionResult,
        comprehension_out,
    )

    # Bug Finding
    bug_finding = ReviewFinding(
        file_path="src/payment.py",
        line_number=11,
        side="RIGHT",
        category=FindingCategory.BUG,
        severity=FindingSeverity.MEDIUM,
        title="Unchecked amount variable could be None",
        description="amount is multiplied without None verification.",
        impact="TypeError raised at runtime if amount is null.",
        recommendation="Validate amount is not None before multiplication.",
        evidence=[
            EvidenceItem(
                type=EvidenceType.CODE,
                file="src/payment.py",
                line_start=10,
                line_end=12,
                description="return amount * 1.1",
            )
        ],
        confidence=0.88,
        agent_name="bug",
    )

    provider.register_structured_response(
        lambda prompt, schema: schema is SpecialistFindingsOutput,
        SpecialistFindingsOutput(findings=[bug_finding], analysis_summary="Found 1 defect"),
    )

    builder = ReviewWorkflowBuilder(provider)
    graph = builder.build()

    initial_state = create_initial_state()
    final_state = await graph.ainvoke(initial_state)

    assert final_state["execution_status"] == "COMPLETED"
    assert len(final_state["validated_findings"]) > 0
    assert final_state["validated_findings"][0].status == FindingStatus.VALID
    assert final_state["total_tokens"] > 0
    assert final_state["estimated_cost"] > 0
    assert len(final_state["agent_runs"]) > 0
    assert len(final_state["agent_traces"]) > 0


@pytest.mark.asyncio
async def test_langgraph_failure_isolation_partial_status():
    """If Security Agent raises an exception, other specialists should complete and status becomes PARTIAL."""
    provider = MockLLMProvider()

    # Comprehension succeeds
    provider.register_structured_response(
        lambda prompt, schema: schema is ComprehensionResult,
        ComprehensionResult(
            intent="Update invoice",
            summary="Payment logic changes",
            functional_changes=["Updated invoice"],
            refactors=[],
            changed_components=["payment"],
            affected_interfaces=[],
            risk_areas=["security: auth risk"],
            relevant_symbols=["calculate"],
        ),
    )

    # Make security prompt fail, while bug/test prompts succeed
    bug_finding = ReviewFinding(
        file_path="src/payment.py",
        line_number=11,
        side="RIGHT",
        category=FindingCategory.BUG,
        severity=FindingSeverity.HIGH,
        title="Division by zero in discount",
        description="Potential divide-by-zero on empty items.",
        impact="Crash on zero amount.",
        recommendation="Guard division with check.",
        evidence=[
            EvidenceItem(
                type=EvidenceType.CODE,
                file="src/payment.py",
                line_start=10,
                line_end=12,
                description="Division without zero check",
            )
        ],
        confidence=0.91,
        agent_name="bug",
    )

    def specialist_handler(prompt: str, schema: type):
        if schema is SpecialistFindingsOutput:
            if "Security Specialist" in prompt or "SECURITY RULES" in prompt or "security vulnerabilities" in prompt:
                raise RuntimeError("Simulated transient Security Agent crash!")
            return SpecialistFindingsOutput(findings=[bug_finding], analysis_summary="Bug specialist OK")
        return None

    provider.register_structured_response(
        lambda p, s: s is SpecialistFindingsOutput,
        specialist_handler,
    )

    builder = ReviewWorkflowBuilder(provider)
    graph = builder.build()

    initial_state = create_initial_state()
    final_state = await graph.ainvoke(initial_state)

    # Review status must be PARTIAL because 1 specialist failed, but Bug specialist succeeded!
    assert final_state["execution_status"] == "PARTIAL"
    # The valid finding from BugAgent was preserved!
    assert len(final_state["validated_findings"]) == 1
    assert final_state["validated_findings"][0].title == "Division by zero in discount"
    # Error for security agent recorded
    assert any("Simulated transient Security Agent crash" in str(e) for e in final_state["errors"])


@pytest.mark.asyncio
async def test_langgraph_documentation_pr_skips_specialists():
    """Documentation-only PR should skip specialists and complete cleanly with 0 findings."""
    provider = MockLLMProvider()
    provider.register_structured_response(
        lambda prompt, schema: schema is ComprehensionResult,
        ComprehensionResult(
            intent="Update documentation",
            summary="Updated README.md instructions",
            functional_changes=[],
            refactors=[],
            changed_components=["docs"],
            affected_interfaces=[],
            risk_areas=[],
            relevant_symbols=[],
            is_documentation_only=True,
        ),
    )

    builder = ReviewWorkflowBuilder(provider)
    graph = builder.build()

    initial_state = create_initial_state(files=["README.md"], changed_lines={"README.md": {"RIGHT": [1, 2]}})
    final_state = await graph.ainvoke(initial_state)

    assert final_state["execution_status"] == "COMPLETED"
    assert len(final_state["selected_specialists"]) == 0
    assert len(final_state["validated_findings"]) == 0
    assert "Documentation-only" in final_state["routing_reason"]


@pytest.mark.asyncio
async def test_langgraph_empty_diff_routing():
    """Empty diff with 0 changed files and 0 hunks should route to empty_diff_node cleanly without LLM calls."""
    provider = MockLLMProvider()
    builder = ReviewWorkflowBuilder(provider)
    graph = builder.build()

    state = create_initial_state(files=[], changed_lines={})
    state["diff_hunks_by_file"] = {}
    final_state = await graph.ainvoke(state)

    assert final_state["is_empty_diff"] is True
    assert final_state["execution_status"] == "COMPLETED"
    assert len(final_state["validated_findings"]) == 0
    assert len(final_state["raw_candidate_findings"]) == 0
    assert final_state["final_review_output"]["status"] == "COMPLETED"
    assert final_state["final_review_output"]["validated_finding_count"] == 0


@pytest.mark.asyncio
async def test_langgraph_terminal_failure_missing_metadata():
    """Missing required identifiers like review_job_id or head_sha should terminate immediately as FAILED."""
    provider = MockLLMProvider()
    builder = ReviewWorkflowBuilder(provider)
    graph = builder.build()

    # Missing review_job_id
    state_no_job = create_initial_state()
    state_no_job["review_job_id"] = ""
    res_no_job = await graph.ainvoke(state_no_job)

    assert res_no_job["is_terminal_failure"] is True
    assert res_no_job["execution_status"] == "FAILED"
    assert res_no_job["final_review_output"]["status"] == "FAILED"
    assert any("review_job_id" in str(e) for e in res_no_job["errors"])

    # Missing head_sha
    state_no_sha = create_initial_state()
    state_no_sha["head_sha"] = ""
    res_no_sha = await graph.ainvoke(state_no_sha)

    assert res_no_sha["is_terminal_failure"] is True
    assert res_no_sha["execution_status"] == "FAILED"
    assert any("head_sha" in str(e) for e in res_no_sha["errors"])


@pytest.mark.asyncio
async def test_langgraph_deduplication_in_graph():
    """DeduplicationEngine in LangGraph should merge duplicate findings across specialists into 1 canonical finding."""
    provider = MockLLMProvider()

    comprehension_out = ComprehensionResult(
        intent="Update payment calculation",
        summary="Changes in payment logic.",
        functional_changes=["Changed tax rate"],
        refactors=[],
        changed_components=["payment"],
        affected_interfaces=[],
        risk_areas=["security"],
        relevant_symbols=["calculate"],
    )
    provider.register_structured_response(
        lambda prompt, schema: schema is ComprehensionResult,
        comprehension_out,
    )

    finding_1 = ReviewFinding(
        file_path="src/payment.py",
        line_number=11,
        side="RIGHT",
        category=FindingCategory.BUG,
        severity=FindingSeverity.HIGH,
        title="Potential None dereference on amount",
        description="Amount multiplied without None check.",
        impact="Crash",
        recommendation="Add check",
        evidence=[EvidenceItem(type=EvidenceType.CODE, file="src/payment.py", line_start=11, line_end=11, description="return amount * 1.1")],
        confidence=0.9,
        agent_name="bug",
    )
    finding_2 = ReviewFinding(
        file_path="src/payment.py",
        line_number=11,
        side="RIGHT",
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.MEDIUM,
        title="Potential None dereference on amount",
        description="Amount multiplied without None check in auth context.",
        impact="Denial of Service",
        recommendation="Add check",
        evidence=[EvidenceItem(type=EvidenceType.CODE, file="src/payment.py", line_start=11, line_end=11, description="return amount * 1.1")],
        confidence=0.85,
        agent_name="security",
    )

    def spec_handler(prompt: str, schema: type):
        if schema is SpecialistFindingsOutput:
            if "Security" in prompt:
                return SpecialistFindingsOutput(findings=[finding_2], analysis_summary="Security scan")
            return SpecialistFindingsOutput(findings=[finding_1], analysis_summary="Bug scan")
        return None

    provider.register_structured_response(
        lambda p, s: s is SpecialistFindingsOutput,
        spec_handler,
    )

    builder = ReviewWorkflowBuilder(provider)
    graph = builder.build()

    initial_state = create_initial_state()
    final_state = await graph.ainvoke(initial_state)

    assert final_state["execution_status"] == "COMPLETED"
    assert len(final_state["raw_candidate_findings"]) == 2
    assert len(final_state["deduplicated_findings"]) == 1
    assert len(final_state["duplicate_findings"]) == 1
    assert len(final_state["validated_findings"]) == 1

    canonical = final_state["deduplicated_findings"][0]
    assert canonical.status == FindingStatus.VALID
    assert "bug" in canonical.source_agents or "security" in canonical.source_agents


@pytest.mark.asyncio
async def test_langgraph_line_validation_rejects_out_of_diff_lines():
    """Findings on lines outside the diff changed-lines index must be rejected by validator_node."""
    provider = MockLLMProvider()

    comprehension_out = ComprehensionResult(
        intent="Update payment",
        summary="Payment logic changes",
        functional_changes=["Update"],
        refactors=[],
        changed_components=["payment"],
        affected_interfaces=[],
        risk_areas=[],
        relevant_symbols=["calculate"],
    )
    provider.register_structured_response(
        lambda prompt, schema: schema is ComprehensionResult,
        comprehension_out,
    )

    # Finding on line 999 (not in lines 10, 11, 12)
    invalid_line_finding = ReviewFinding(
        file_path="src/payment.py",
        line_number=999,
        side="RIGHT",
        category=FindingCategory.BUG,
        severity=FindingSeverity.LOW,
        title="Unrelated issue far below diff",
        description="Issue outside modified diff.",
        impact="Low",
        recommendation="Fix",
        evidence=[EvidenceItem(type=EvidenceType.CODE, file="src/payment.py", line_start=999, line_end=999, description="pass")],
        confidence=0.7,
        agent_name="bug",
    )

    provider.register_structured_response(
        lambda p, s: s is SpecialistFindingsOutput,
        SpecialistFindingsOutput(findings=[invalid_line_finding], analysis_summary="Bug findings"),
    )

    builder = ReviewWorkflowBuilder(provider)
    graph = builder.build()

    initial_state = create_initial_state()
    final_state = await graph.ainvoke(initial_state)

    assert len(final_state["validated_findings"]) == 0
    assert len(final_state["invalid_findings"]) == 1
    assert final_state["invalid_findings"][0].status == FindingStatus.INVALID
    assert "diff lines" in final_state["invalid_findings"][0].validation_notes.lower() or "line" in final_state["invalid_findings"][0].validation_notes.lower()


@pytest.mark.asyncio
async def test_langgraph_comprehension_error_isolated():
    """If comprehension agent encounters an API exception, review falls back to defaults and proceeds to specialists."""
    provider = MockLLMProvider()

    def comp_fail(prompt: str, schema: type):
        if schema is ComprehensionResult:
            raise RuntimeError("Gemini 429 ResourceExhausted: rate limit exceeded")
        return None

    provider.register_structured_response(
        lambda p, s: s is ComprehensionResult,
        comp_fail,
    )

    bug_finding = ReviewFinding(
        file_path="src/payment.py",
        line_number=11,
        side="RIGHT",
        category=FindingCategory.BUG,
        severity=FindingSeverity.MEDIUM,
        title="Fallback bug finding",
        description="Found by specialist despite comprehension failure.",
        impact="Runtime crash during checkout transaction.",
        recommendation="Validate amount is not None before multiplication.",
        evidence=[EvidenceItem(type=EvidenceType.CODE, file="src/payment.py", line_start=11, line_end=11, description="amount * 1.1")],
        confidence=0.8,
        agent_name="bug",
    )

    provider.register_structured_response(
        lambda p, s: s is SpecialistFindingsOutput,
        SpecialistFindingsOutput(findings=[bug_finding], analysis_summary="Found defect"),
    )

    builder = ReviewWorkflowBuilder(provider)
    graph = builder.build()

    initial_state = create_initial_state()
    final_state = await graph.ainvoke(initial_state)

    # Workflow did not crash!
    assert final_state["execution_status"] == "PARTIAL"
    assert any("ResourceExhausted" in str(e) for e in final_state["errors"])
    # Specialist was still executed and finding validated
    assert len(final_state["validated_findings"]) >= 1
    assert final_state["final_review_output"]["status"] == "PARTIAL"


@pytest.mark.asyncio
async def test_langgraph_final_review_output_structure():
    """Verify that final_review_output adheres to structured review schema."""
    provider = MockLLMProvider()

    provider.register_structured_response(
        lambda prompt, schema: schema is ComprehensionResult,
        ComprehensionResult(
            intent="Test schema",
            summary="Testing final review output structure",
            functional_changes=[],
            refactors=[],
            changed_components=[],
            affected_interfaces=[],
            risk_areas=[],
            relevant_symbols=[],
        ),
    )
    provider.register_structured_response(
        lambda prompt, schema: schema is SpecialistFindingsOutput,
        SpecialistFindingsOutput(findings=[], analysis_summary="Clean"),
    )

    builder = ReviewWorkflowBuilder(provider)
    graph = builder.build()

    initial_state = create_initial_state()
    final_state = await graph.ainvoke(initial_state)

    out = final_state.get("final_review_output")
    assert isinstance(out, dict)
    assert out["review_job_id"] == "job-12345"
    assert out["status"] == "COMPLETED"
    assert "Testing final review output structure" in out["summary"]
    assert "validated_finding_count" in out
    assert "invalid_finding_count" in out
    assert "deduplicated_count" in out
    assert "duplicate_count" in out
    assert "specialists_run" in out
    assert "total_tokens" in out
    assert "estimated_cost" in out
    assert "errors" in out

