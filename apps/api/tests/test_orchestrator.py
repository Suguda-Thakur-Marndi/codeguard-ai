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
    f_list = files or ["src/payment.py"]
    lines = changed_lines or {"src/payment.py": {"RIGHT": [10, 11, 12], "LEFT": []}}
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
