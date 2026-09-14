"""Tests for DeduplicationEngine, Root-Cause Grouping, and Confidence Policy (Phase 4)."""


from app.agents.judge.confidence import ConfidencePolicy
from app.agents.judge.deduplication import DeduplicationEngine
from app.agents.judge.schemas import JudgeDecisionType
from app.agents.schemas.finding import (
    FindingCategory,
    FindingSeverity,
    FindingStatus,
    ReviewFinding,
)


def test_confidence_policy_rejected():
    """Confidence must be 0.0 when finding is rejected."""
    conf = ConfidencePolicy.calculate(
        specialist_confidence=0.95,
        judge_confidence=0.90,
        decision=JudgeDecisionType.REJECT,
    )
    assert conf == 0.0


def test_confidence_policy_weighted_and_bonus():
    """Confidence uses 0.35 spec + 0.65 judge + 0.05 execution bonus."""
    # 0.35 * 0.90 + 0.65 * 0.90 = 0.90 -> +0.05 execution passed = 0.95
    conf = ConfidencePolicy.calculate(
        specialist_confidence=0.90,
        judge_confidence=0.90,
        decision=JudgeDecisionType.ACCEPT,
        execution_passed=True,
    )
    assert conf == 0.95


def test_confidence_policy_downgrade_penalty():
    """Confidence deducts 0.05 when severity is downgraded from HIGH to LOW."""
    # 0.35 * 0.80 + 0.65 * 0.80 = 0.80 -> downgrade penalty (-0.05) = 0.75
    conf = ConfidencePolicy.calculate(
        specialist_confidence=0.80,
        judge_confidence=0.80,
        decision=JudgeDecisionType.ACCEPT,
        original_severity="HIGH",
        final_severity="LOW",
        execution_passed=False,
    )
    assert conf == 0.75


def test_deduplicate_security_and_bug_agents():
    """Security and Bug agents reporting same issue at line 142 should merge into one canonical finding with both source agents."""
    f1 = ReviewFinding(
        agent_name="security_agent",
        file_path="src/payment_service.py",
        line_number=142,
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.HIGH,
        title="Missing authorization validation on refund",
        description="User permissions are not verified before issuing refund.",
        impact="Unauthorized users can trigger financial refunds.",
        recommendation="Verify caller role using AuthContext.verify_permission('refund').",
        confidence=0.90,
        source_agents=["security_agent"],
    )
    f2 = ReviewFinding(
        agent_name="bug_agent",
        file_path="src/payment_service.py",
        line_number=142,
        category=FindingCategory.BUG,
        severity=FindingSeverity.HIGH,
        title="Unauthorized users can trigger refund",
        description="Any authenticated user can invoke the refund endpoint directly.",
        impact="Financial loss.",
        recommendation="Verify permission before calling PaymentGateway.refund().",
        confidence=0.85,
        source_agents=["bug_agent"],
    )

    canonical, duplicates = DeduplicationEngine.deduplicate_and_group([f1, f2])

    assert len(canonical) == 1
    assert len(duplicates) == 1

    primary = canonical[0]
    dup = duplicates[0]

    # Check that provenance includes both agents
    assert "security_agent" in primary.source_agents
    assert "bug_agent" in primary.source_agents

    # Duplicate marked as rejected with duplicate_of pointer
    assert dup.status == FindingStatus.REJECTED
    assert dup.duplicate_of == primary.finding_id


def test_root_cause_grouping_distinct_lines():
    """Two different findings in same file sharing a root defect (e.g. auth failure) should receive the same root_cause_id."""
    f1 = ReviewFinding(
        agent_name="security_agent",
        file_path="src/payment_service.py",
        line_number=45,
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.HIGH,
        title="Missing authorization check on payment init",
        description="No auth check before initialize_payment.",
        impact="Unauthorized payments.",
        recommendation="Add auth check.",
        confidence=0.90,
    )
    f2 = ReviewFinding(
        agent_name="security_agent",
        file_path="src/payment_service.py",
        line_number=180,  # Far away line: not a duplicate
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.HIGH,
        title="Missing authorization check on refund cancel",
        description="No auth check before cancel_refund.",
        impact="Unauthorized cancellations.",
        recommendation="Add auth check.",
        confidence=0.85,
    )

    canonical, duplicates = DeduplicationEngine.deduplicate_and_group([f1, f2])

    assert len(canonical) == 2
    assert len(duplicates) == 0

    # Because both share auth root cause in payment_service, they get grouped under same root_cause_id
    assert canonical[0].root_cause_id is not None
    assert canonical[0].root_cause_id == canonical[1].root_cause_id
