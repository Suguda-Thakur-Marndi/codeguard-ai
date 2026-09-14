"""Tests for PromptRegistry, RiskRouter, and Specialist Agents (Comprehension, Security, Bug, Test)."""

import pytest

from app.agents.llm.mock import MockLLMProvider
from app.agents.orchestrator.router import RiskRouter
from app.agents.prompts.registry import PromptRegistry
from app.agents.schemas.comprehension import ComprehensionResult
from app.agents.schemas.finding import (
    EvidenceItem,
    EvidenceType,
    FindingCategory,
    FindingSeverity,
    ReviewFinding,
    SpecialistFindingsOutput,
)
from app.agents.specialists.bug import BugAgent
from app.agents.specialists.comprehension import ComprehensionAgent
from app.agents.specialists.security import SecurityAgent
from app.agents.specialists.test_agent import TestAgent


def test_prompt_registry_prompt_injection_defense():
    """PromptRegistry must include anti-prompt-injection instructions in system prompts."""
    system_prompt = PromptRegistry.get_system_prompt("security.v1")
    assert "DATA" in system_prompt or "instructions" in system_prompt
    assert "prompt injection" in system_prompt.lower() or "untrusted data" in system_prompt.lower()


def test_prompt_registry_valid_lines_injection():
    """PromptRegistry format_user_prompt must inject allowed valid changed lines."""
    user_prompt = PromptRegistry.format_user_prompt(
        agent_name="security",
        version="security.v1",
        context_payload={"diff_hunk": "@@ -10,3 +10,4 @@"},
        valid_lines_by_file={"src/payment.py": [10, 11, 12]},
    )
    assert "src/payment.py" in user_prompt
    assert "[10, 11, 12]" in user_prompt
    assert "STRICT LINE NUMBER CONSTRAINT" in user_prompt


def test_risk_router_documentation_only():
    """RiskRouter should skip all specialists for documentation-only PRs."""
    comprehension = ComprehensionResult(
        intent="Update project documentation and README",
        summary="Adds usage notes to README.md",
        functional_changes=[],
        refactors=[],
        changed_components=["docs"],
        affected_interfaces=[],
        risk_areas=[],
        relevant_symbols=[],
    )
    specialists, reason = RiskRouter.route(
        comprehension=comprehension,
        changed_files=["README.md", "docs/architecture.md"],
    )
    assert specialists == []
    assert "Documentation" in reason


def test_risk_router_security_sensitive():
    """RiskRouter should route security-risk PRs to Security and Bug specialists."""
    comprehension = ComprehensionResult(
        intent="Modify auth token validation",
        summary="Changes token parsing logic",
        functional_changes=["Updated JWT verification"],
        refactors=[],
        changed_components=["auth"],
        affected_interfaces=["AuthService"],
        risk_areas=["security: auth token bypass risks"],
        relevant_symbols=["verify_token"],
    )
    specialists, reason = RiskRouter.route(
        comprehension=comprehension,
        changed_files=["src/auth/service.py"],
    )
    assert "security" in specialists
    assert "bug" in specialists


def test_risk_router_contract_change():
    """RiskRouter should route API/interface contract changes to Bug, Test, and Security specialists."""
    comprehension = ComprehensionResult(
        intent="Change refund API response payload and signature",
        summary="Modifies refund endpoint contract",
        functional_changes=["Changed return type"],
        refactors=[],
        changed_components=["api"],
        affected_interfaces=["RefundAPI"],
        risk_areas=[],
        relevant_symbols=["refund"],
    )
    specialists, reason = RiskRouter.route(
        comprehension=comprehension,
        changed_files=["src/api/refund.py"],
    )
    assert "bug" in specialists
    assert "test" in specialists
    assert "security" in specialists


def test_risk_router_performance_sensitive():
    """RiskRouter should route performance-risk PRs to Performance, Bug, and Test specialists."""
    comprehension = ComprehensionResult(
        intent="Batch process records in memory loop",
        summary="Nested iterations over database records",
        functional_changes=["Added batch processor"],
        refactors=[],
        changed_components=["worker"],
        affected_interfaces=[],
        risk_areas=["performance: accidental O(n^2) nested loop"],
        relevant_symbols=["batch_process"],
        has_performance_impact=True,
    )
    specialists, reason = RiskRouter.route(
        comprehension=comprehension,
        changed_files=["src/worker/batch.py"],
    )
    assert "performance" in specialists
    assert "bug" in specialists
    assert "test" in specialists


@pytest.mark.asyncio
async def test_comprehension_agent_execution():
    """ComprehensionAgent should return structured ComprehensionResult with run metadata."""
    provider = MockLLMProvider()
    expected = ComprehensionResult(
        intent="Refactor refund handler",
        summary="Extracts helper function in refund flow",
        functional_changes=["Added validate_refund helper"],
        refactors=["Refactored refund method"],
        changed_components=["refund_service"],
        affected_interfaces=[],
        risk_areas=[],
        relevant_symbols=["refund", "validate_refund"],
    )
    provider.register_structured_response(
        lambda prompt, schema: schema is ComprehensionResult,
        expected,
    )

    agent = ComprehensionAgent(provider)
    result, run_meta = await agent.run(
        title="Refactor refund",
        description="Helper extraction",
        base_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        head_sha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        diff_hunks_by_file={"src/refund.py": [{"new_start": 10, "new_lines": 5, "lines": []}]},
        ast_chunks_by_file={},
        context_by_symbol={},
    )

    assert result == expected
    assert run_meta["agent_name"] == "comprehension"
    assert run_meta["total_tokens"] > 0
    assert run_meta.get("error_message") is None


@pytest.mark.asyncio
async def test_security_agent_finds_vulnerability():
    """SecurityAgent should return ReviewFinding with grounded evidence on insecure code."""
    provider = MockLLMProvider()
    finding = ReviewFinding(
        file_path="src/payment.py",
        line_number=45,
        side="RIGHT",
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.HIGH,
        title="Missing Authorization Check on Refund",
        description="Refund execution is initiated without role or caller authorization verification.",
        impact="An unprivileged caller can trigger arbitrary refunds.",
        recommendation="Verify caller role permissions before executing payment refund.",
        evidence=[
            EvidenceItem(
                type=EvidenceType.CODE,
                file="src/payment.py",
                line_start=44,
                line_end=46,
                description="Direct call to refund gateway without auth guard.",
            )
        ],
        confidence=0.92,
        affected_symbol="PaymentService.refund",
        agent_name="security",
    )
    provider.register_structured_response(
        lambda prompt, schema: schema is SpecialistFindingsOutput,
        SpecialistFindingsOutput(findings=[finding], analysis_summary="Found 1 security defect"),
    )

    agent = SecurityAgent(provider)
    output, run_meta = await agent.run(
        changed_lines_by_file={"src/payment.py": {"added": [45], "deleted": []}},
        diff_hunks_by_file={"src/payment.py": [{"old_start": 40, "old_lines": 10, "new_start": 40, "new_lines": 10, "lines": []}]},
        ast_chunks_by_file={},
        source_code_by_file={"src/payment.py": "def refund(): pass"},
        context_by_symbol={},
    )

    assert len(output.findings) == 1
    assert output.findings[0].category == FindingCategory.SECURITY
    assert output.findings[0].line_number == 45
    assert len(output.findings[0].evidence) == 1
    assert output.findings[0].evidence[0].type == EvidenceType.CODE


@pytest.mark.asyncio
async def test_security_agent_safe_code_no_finding():
    """SecurityAgent must return NO_FINDING (0 findings) on safe code with auth checks."""
    provider = MockLLMProvider()
    # Explicitly configure mock to return 0 findings (safe code)
    provider.register_structured_response(
        lambda prompt, schema: schema is SpecialistFindingsOutput,
        SpecialistFindingsOutput(findings=[], analysis_summary="Safe code: proper authorization guard present."),
    )

    agent = SecurityAgent(provider)
    output, run_meta = await agent.run(
        changed_lines_by_file={"src/payment.py": {"added": [45], "deleted": []}},
        diff_hunks_by_file={"src/payment.py": [{"old_start": 40, "old_lines": 10, "new_start": 40, "new_lines": 10, "lines": []}]},
        ast_chunks_by_file={},
        source_code_by_file={"src/payment.py": "def refund(): pass"},
        context_by_symbol={},
    )

    assert len(output.findings) == 0
    assert "Safe code" in output.analysis_summary


@pytest.mark.asyncio
async def test_bug_agent_finds_defect():
    """BugAgent should return ReviewFinding for unhandled exception or None dereference."""
    provider = MockLLMProvider()
    finding = ReviewFinding(
        file_path="src/gateway.py",
        line_number=88,
        side="RIGHT",
        category=FindingCategory.ERROR_HANDLING,
        severity=FindingSeverity.HIGH,
        title="Uncaught ConnectionError in HTTP Retry Loop",
        description="Network socket error propagates without catch or resource closure.",
        impact="Process terminates unexpectedly on network hiccup.",
        recommendation="Wrap connection attempt in try/except ConnectionError and close socket.",
        evidence=[
            EvidenceItem(
                type=EvidenceType.CODE,
                file="src/gateway.py",
                line_start=87,
                line_end=89,
                description="Bare socket call in loop",
            )
        ],
        confidence=0.89,
        agent_name="bug",
    )
    provider.register_structured_response(
        lambda prompt, schema: schema is SpecialistFindingsOutput,
        SpecialistFindingsOutput(findings=[finding], analysis_summary="Found 1 error handling defect"),
    )

    agent = BugAgent(provider)
    output, run_meta = await agent.run(
        changed_lines_by_file={"src/gateway.py": {"added": [88], "deleted": []}},
        diff_hunks_by_file={"src/gateway.py": [{"old_start": 80, "old_lines": 10, "new_start": 80, "new_lines": 10, "lines": []}]},
        ast_chunks_by_file={},
        source_code_by_file={"src/gateway.py": "def connect(): pass"},
        context_by_symbol={},
    )

    assert len(output.findings) == 1
    assert output.findings[0].category == FindingCategory.ERROR_HANDLING
    assert output.findings[0].line_number == 88


@pytest.mark.asyncio
async def test_test_agent_finds_untested_branch():
    """TestAgent should return ReviewFinding when critical branch has no unit test coverage."""
    provider = MockLLMProvider()
    finding = ReviewFinding(
        file_path="src/validator.py",
        line_number=24,
        side="RIGHT",
        category=FindingCategory.TEST_COVERAGE,
        severity=FindingSeverity.MEDIUM,
        title="Missing Test Coverage for Malformed Token Exception Path",
        description="The branch handling MalformedTokenError has no corresponding test case in test_validator.py.",
        impact="Regressions in malformed token handling will go undetected.",
        recommendation="Add unit test test_validate_token_malformed_raises_error to test_validator.py.",
        evidence=[
            EvidenceItem(
                type=EvidenceType.CODE,
                file="src/validator.py",
                line_start=23,
                line_end=25,
                description="raise MalformedTokenError branch",
            )
        ],
        confidence=0.85,
        agent_name="test",
    )
    provider.register_structured_response(
        lambda prompt, schema: schema is SpecialistFindingsOutput,
        SpecialistFindingsOutput(findings=[finding], analysis_summary="Found 1 test coverage defect"),
    )

    agent = TestAgent(provider)
    output, run_meta = await agent.run(
        changed_lines_by_file={"src/validator.py": {"added": [24], "deleted": []}},
        diff_hunks_by_file={"src/validator.py": [{"old_start": 20, "old_lines": 10, "new_start": 20, "new_lines": 10, "lines": []}]},
        ast_chunks_by_file={},
        source_code_by_file={"src/validator.py": "def validate(): pass"},
        context_by_symbol={},
    )

    assert len(output.findings) == 1
    assert output.findings[0].category == FindingCategory.TEST_COVERAGE
    assert output.findings[0].line_number == 24
