"""Tests for AdversarialJudge and its validation gates (Phase 4)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.judge.adversarial_judge import AdversarialJudge
from app.agents.judge.schemas import JudgeDecision, JudgeDecisionType
from app.agents.llm.provider import LLMProvider, LLMResponse, TokenUsage
from app.agents.prompts.registry import PromptRegistry
from app.agents.schemas.finding import FindingCategory, FindingSeverity, ReviewFinding


@pytest.fixture
def sample_valid_lines():
    return {
        "src/payment_service.py": {
            "RIGHT": [140, 141, 142, 143],
            "LEFT": [],
        }
    }


@pytest.fixture
def mock_llm_provider():
    provider = MagicMock(spec=LLMProvider)
    return provider


def test_gate1_valid_diff_location(sample_valid_lines, mock_llm_provider):
    """Gate 1 should pass when the finding line is in the PR changed lines."""
    judge = AdversarialJudge(mock_llm_provider)
    finding = ReviewFinding(
        agent_name="security_agent",
        file_path="src/payment_service.py",
        line_number=142,
        side="RIGHT",
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.HIGH,
        title="Missing authorization validation",
        description="Missing permission check before processing refund.",
        impact="Unauthorized users can trigger financial refunds.",
        recommendation="Verify caller role using AuthContext.verify_permission('refund').",
        confidence=0.9,
    )
    passed, reason = judge.evaluate_gate1_diff_boundary(
        finding=finding,
        changed_files=["src/payment_service.py"],
        valid_lines_by_file=sample_valid_lines,
    )
    assert passed is True
    assert reason is None


def test_gate1_invalid_line_number_rejected_without_llm(sample_valid_lines, mock_llm_provider):
    """Gate 1 must deterministically reject when finding points to an un-changed or hallucinated line (e.g. 9999)."""
    judge = AdversarialJudge(mock_llm_provider)
    finding = ReviewFinding(
        agent_name="security_agent",
        file_path="src/payment_service.py",
        line_number=9999,  # Hallucinated line!
        side="RIGHT",
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.HIGH,
        title="Missing authorization validation",
        description="Line 9999 is vulnerable.",
        impact="Potential breach.",
        recommendation="Fix line 9999.",
        confidence=0.9,
    )
    passed, reason = judge.evaluate_gate1_diff_boundary(
        finding=finding,
        changed_files=["src/payment_service.py"],
        valid_lines_by_file=sample_valid_lines,
    )
    assert passed is False
    assert "Allowed lines" in reason


@pytest.mark.asyncio
async def test_evaluate_finding_gate1_rejection_no_tokens(sample_valid_lines, mock_llm_provider):
    """Gate 1 rejection must return 0 tokens and cost without invoking the LLM provider."""
    judge = AdversarialJudge(mock_llm_provider)
    finding = ReviewFinding(
        agent_name="security_agent",
        file_path="src/payment_service.py",
        line_number=9999,
        side="RIGHT",
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.HIGH,
        title="Hallucinated line issue",
        description="Line 9999 issue.",
        impact="Risk of defect.",
        recommendation="Check caller context.",
        confidence=0.9,
    )

    decision, meta = await judge.evaluate_finding(
        finding=finding,
        changed_files=["src/payment_service.py"],
        valid_lines_by_file=sample_valid_lines,
        diff_hunks=[],
        source_and_ast_context="",
        caller_and_guard_context="",
        existing_tests_context="",
    )

    assert decision.decision == JudgeDecisionType.REJECT
    assert decision.boundary_passed is False
    assert decision.rejection_reason == "INVALID_DIFF_LOCATION"
    assert meta["total_tokens"] == 0
    assert meta["estimated_cost"] == 0.0
    mock_llm_provider.generate_structured.assert_not_called()


@pytest.mark.asyncio
async def test_gate2_existing_guard_mitigation(sample_valid_lines, mock_llm_provider):
    """Gate 2 rejects when caller context contains existing mitigation guards."""
    judge = AdversarialJudge(mock_llm_provider)
    finding = ReviewFinding(
        agent_name="security_agent",
        file_path="src/payment_service.py",
        line_number=142,
        side="RIGHT",
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.HIGH,
        title="Missing authorization validation",
        description="Payment refund does not check if user is admin.",
        impact="Unauthorized refunds.",
        recommendation="Enforce user.has_perm('refund') before refund.",
        confidence=0.9,
    )

    # Mock Judge LLM detecting the caller guard
    mock_decision = JudgeDecision(
        finding_id=finding.finding_id,
        decision=JudgeDecisionType.REJECT,
        final_severity=FindingSeverity.HIGH,
        judge_confidence=0.95,
        final_confidence=0.0,
        boundary_passed=True,
        factuality_passed=False,
        actionability_passed=True,
        severity_passed=True,
        rejection_reason="FACTUALITY_FAILURE: Existing authorization guard in caller handle_refund_request already prevents unauthorized execution.",
        verification_summary="Rejected due to existing guard outside the immediate hunk.",
    )
    mock_llm_provider.generate_structured = AsyncMock(
        return_value=LLMResponse(
            data=mock_decision,
            token_usage=TokenUsage(
                input_tokens=500,
                output_tokens=100,
                total_tokens=600,
                estimated_cost=0.001,
            ),
            latency_ms=250.0,
            model_name="gemini-2.5-pro",
        )
    )

    decision, meta = await judge.evaluate_finding(
        finding=finding,
        changed_files=["src/payment_service.py"],
        valid_lines_by_file=sample_valid_lines,
        diff_hunks=[{"header": "@@ -140,5 +140,8 @@", "lines": ["+    refund = PaymentGateway.refund()"]}],
        source_and_ast_context="def process_refund(): ...",
        caller_and_guard_context="Caller handle_refund_request() checks user.has_perm('refund')",
        existing_tests_context="test_refund_denies_unauthorized() covers this flow",
    )

    assert decision.decision == JudgeDecisionType.REJECT
    assert decision.factuality_passed is False
    assert "Existing authorization guard" in decision.rejection_reason
    assert decision.final_confidence == 0.0


def test_gate3_vague_actionability_heuristic(mock_llm_provider):
    """Gate 3 rejects vague suggestions such as 'consider adding error handling'."""
    judge = AdversarialJudge(mock_llm_provider)
    assert judge._is_vague_recommendation("Consider adding error handling.") is True
    assert judge._is_vague_recommendation("Improve readability") is True
    assert judge._is_vague_recommendation(
        "Wrap the PaymentGateway.refund call in a try/except GatewayTimeoutException block and trigger compensation rollback."
    ) is False


def test_prompt_injection_guardrail():
    """Verify that Judge prompt instructions explicitly mandate treating repo code as untrusted DATA."""
    system_prompt = PromptRegistry.get_system_prompt("judge.v1")
    assert "DATA" in system_prompt or "untrusted" in system_prompt.lower()
    assert "ignore" in system_prompt.lower()
