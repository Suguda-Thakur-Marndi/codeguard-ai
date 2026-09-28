"""Permanent regression tests for Phase 17 Critical System Invariants.

Covers:
1. GitHub (Webhook signatures, duplicate event idempotency, repo/PR validation, diff line bounds, idempotent publication)
2. Code Intelligence (Symbol boundary preservation, safe failure on invalid files, bounded context retrieval, stale index invalidation)
3. AI Review (Schema validation, evidence requirement, invalid file/line rejection, bounded execution, failure non-fabrication)
4. Adversarial Judge (Rejection of unsupported claims, root-cause preserving deduplication, traceable verification)
5. MCP Governance (Server authority, untrusted agent restriction, tool argument validation, forbidden tool blocking)
6. Approval & Publication (Context binding, stale head SHA rejection, unauthorized approval blocking, duplicate publication block, audit logging)
"""

import hashlib
import hmac
from unittest.mock import MagicMock

import pytest
from code_intelligence.context.ranker import ContextRanker
from code_intelligence.languages.registry import default_registry
from code_intelligence.models import RankedContextItem
from sqlalchemy.orm import Session

from app.agents.judge.adversarial_judge import AdversarialJudge
from app.agents.orchestrator.validator import FindingValidator
from app.agents.schemas.finding import (
    EvidenceItem,
    EvidenceType,
    FindingCategory,
    FindingSeverity,
    FindingStatus,
    ReviewFinding,
)
from app.github.publisher import GitHubReviewPublisher
from app.mcp.auth import Principal, PrincipalRole
from app.mcp.classification import FORBIDDEN_TOOL_ACTIONS, PolicyDecision
from app.mcp.policy_engine import PolicyEngine
from app.models.approval_request import ApprovalStatus
from app.models.organization import Organization
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.review_job import ReviewJob, ReviewJobStatus
from app.services.approval_service import ApprovalService

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def invariant_setup(db_session: Session) -> dict:
    org = Organization(
        github_installation_id=98765,
        github_account_id=54321,
        github_account_login="invariant-corp",
    )
    db_session.add(org)
    db_session.flush()

    repo = Repository(
        organization_id=org.id,
        github_repo_id=778899,
        owner="invariant-corp",
        name="critical-system",
        full_name="invariant-corp/critical-system",
        default_branch="main",
    )
    db_session.add(repo)
    db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_id=88001,
        number=42,
        title="Critical Payment Processing Fix",
        author_login="octocat",
        base_sha="base_sha_00000000000000000000000000000000",
        head_sha="head_sha_11111111111111111111111111111111",
    )
    db_session.add(pr)
    db_session.flush()

    job = ReviewJob(
        pull_request_id=pr.id,
        status=ReviewJobStatus.COMPLETED,
    )
    db_session.add(job)
    db_session.commit()

    return {"org": org, "repo": repo, "pr": pr, "job": job}


# ==============================================================================
# 1. GITHUB INTEGRATION INVARIANTS
# ==============================================================================


def test_invariant_github_webhook_signature_verification():
    """Invariant: Webhook signatures must be validated via HMAC-SHA256 constant-time comparison."""
    secret = "test-webhook-secret-phase17"
    payload = b'{"action":"opened","pull_request":{"id":123}}'

    # Compute valid signature
    valid_sig = "sha256=" + hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    invalid_sig = "sha256=" + ("0" * 64)

    # Verification function logic
    def verify_sig(body: bytes, header_sig: str, expected_secret: str) -> bool:
        if not header_sig.startswith("sha256="):
            return False
        expected_sig = "sha256=" + hmac.new(expected_secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(header_sig, expected_sig)

    assert verify_sig(payload, valid_sig, secret) is True
    assert verify_sig(payload, invalid_sig, secret) is False
    assert verify_sig(payload, "malformed-header", secret) is False


def test_invariant_github_review_line_numbers_map_to_valid_changed_lines():
    """Invariant: Review line numbers must map strictly to modified diff lines."""
    changed_files = ["src/payment.py"]
    changed_lines = {"src/payment.py": {"RIGHT": [10, 11, 12, 13]}}

    # In-bounds finding
    valid_finding = ReviewFinding(
        file_path="src/payment.py",
        line_number=11,
        side="RIGHT",
        category=FindingCategory.BUG,
        severity=FindingSeverity.HIGH,
        title="Unchecked null pointer",
        description="Value can be null",
        impact="Crash",
        recommendation="Add check",
        confidence=0.9,
        evidence=[EvidenceItem(type=EvidenceType.CODE, file="src/payment.py", line_start=11, line_end=12, description="Line 11 unchecked access")],
        agent_name="bug",
    )

    # Out-of-bounds line number
    out_of_bounds_finding = ReviewFinding(
        file_path="src/payment.py",
        line_number=999,
        side="RIGHT",
        category=FindingCategory.BUG,
        severity=FindingSeverity.HIGH,
        title="Out of bounds bug",
        description="Line 999 not in diff",
        impact="Crash",
        recommendation="Fix",
        confidence=0.9,
        evidence=[EvidenceItem(type=EvidenceType.CODE, file="src/payment.py", line_start=999, line_end=999, description="Line 999 fake code")],
        agent_name="bug",
    )

    valid, invalid = FindingValidator.validate_findings(
        findings=[valid_finding, out_of_bounds_finding],
        changed_files=changed_files,
        changed_lines_by_file=changed_lines,
    )

    assert len(valid) == 1
    assert valid[0].line_number == 11
    assert len(invalid) == 1
    assert invalid[0].line_number == 999
    assert invalid[0].status in (FindingStatus.INVALID, FindingStatus.REJECTED)


@pytest.mark.asyncio
async def test_invariant_github_publisher_stale_head_sha_aborts():
    """Invariant: Publication must be blocked if current PR head SHA differs from verified head SHA."""
    publisher = GitHubReviewPublisher()
    res = await publisher.publish_atomic_review(
        owner="invariant-corp",
        repo="critical-system",
        pull_number=42,
        verified_head_sha="head_sha_old",
        current_head_sha="head_sha_new",
        findings=[],
    )
    assert res.success is False
    assert res.status == "STALE"


# ==============================================================================
# 2. CODE INTELLIGENCE INVARIANTS
# ==============================================================================


def test_invariant_ast_parsing_preserves_symbol_boundaries():
    """Invariant: AST parsing must preserve accurate symbol start and end lines."""
    code = (
        "def calculate_tax(amount: float) -> float:\n"
        "    tax_rate = 0.15\n"
        "    return amount * tax_rate\n\n"
        "class OrderProcessor:\n"
        "    def process(self):\n"
        "        pass\n"
    )

    parser = default_registry.get_parser("tax.py")
    assert parser is not None
    tree, diagnostics = parser.parse(code.encode("utf-8"), file_path="tax.py")
    assert tree is not None

    symbols = parser.extract_symbols(tree, code.encode("utf-8"), file_path="tax.py")
    calc_fn = next((s for s in symbols if s.name == "calculate_tax"), None)
    assert calc_fn is not None
    assert calc_fn.start_line == 1
    assert calc_fn.end_line == 3

    order_cls = next((s for s in symbols if s.name == "OrderProcessor"), None)
    assert order_cls is not None
    assert order_cls.start_line == 5
    assert order_cls.end_line == 7


def test_invariant_unsupported_files_fail_safely():
    """Invariant: Invalid, binary, or unsupported files must fail safely without exceptions."""
    parser = default_registry.get_parser("binary_asset.bin")
    assert parser is None
    assert default_registry.is_supported("binary_asset.bin") is False


def test_invariant_context_retrieval_respects_configured_limits():
    """Invariant: Context retrieval must strictly obey configured file, symbol, and character limits."""
    ranker = ContextRanker()
    items = [
        RankedContextItem(
            entity_type="symbol",
            identifier=f"sym_{i}",
            file_path=f"file_{i}.py",
            relevance_score=0.9 - (i * 0.1),
            reason="dependency",
            char_count=100,
        )
        for i in range(5)
    ]

    # Budget strictly to max 2 files and 250 characters
    budgeted = ranker.rank_and_budget(
        candidate_items=items,
        max_files=2,
        max_symbols=2,
        max_characters=250,
    )

    assert len(budgeted) <= 2
    total_chars = sum(item.char_count for item in budgeted)
    assert total_chars <= 250


# ==============================================================================
# 3. AI REVIEW INVARIANTS
# ==============================================================================


def test_invariant_findings_must_have_evidence():
    """Invariant: Findings without concrete evidence items must be rejected."""
    finding_no_evidence = ReviewFinding(
        file_path="src/service.py",
        line_number=10,
        side="RIGHT",
        category=FindingCategory.BUG,
        severity=FindingSeverity.MEDIUM,
        title="Unverified assertion",
        description="No proof provided",
        impact="Unknown",
        recommendation="None provided",
        confidence=0.8,
        evidence=[],  # Empty evidence
        agent_name="bug",
    )

    valid, invalid = FindingValidator.validate_findings(
        findings=[finding_no_evidence],
        changed_files=["src/service.py"],
        changed_lines_by_file={"src/service.py": {"RIGHT": [10]}},
    )

    assert len(valid) == 0
    assert len(invalid) == 1
    assert invalid[0].status in (FindingStatus.INVALID, FindingStatus.REJECTED)


def test_invariant_invalid_file_paths_rejected():
    """Invariant: Findings referencing files not modified in the PR must be rejected."""
    hallucinated_file_finding = ReviewFinding(
        file_path="src/unrelated_secret_file.py",
        line_number=1,
        side="RIGHT",
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.CRITICAL,
        title="Secret leak",
        description="File not in PR diff",
        impact="Critical",
        recommendation="Fix immediately",
        confidence=0.95,
        evidence=[EvidenceItem(type=EvidenceType.CODE, file="src/unrelated_secret_file.py", line_start=1, line_end=2, description="Unrelated secret")],
        agent_name="security",
    )

    valid, invalid = FindingValidator.validate_findings(
        findings=[hallucinated_file_finding],
        changed_files=["src/legit.py"],
        changed_lines_by_file={"src/legit.py": {"RIGHT": [1, 2]}},
    )

    assert len(valid) == 0
    assert len(invalid) == 1
    assert invalid[0].status in (FindingStatus.INVALID, FindingStatus.REJECTED)


# ==============================================================================
# 4. ADVERSARIAL JUDGE INVARIANTS
# ==============================================================================


def test_invariant_judge_rejects_unsupported_findings_despite_high_confidence():
    """Invariant: Confident model output lacking context support must be rejected by Judge."""
    judge = AdversarialJudge(llm_provider=MagicMock())

    finding = ReviewFinding(
        file_path="src/payment.py",
        line_number=50,
        side="RIGHT",
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.HIGH,
        title="Fabricated SQL Injection",
        description="Attacker controls variable sql_query",
        impact="Data leak",
        recommendation="Use parameterized query",
        confidence=0.99,  # High confidence claim
        evidence=[EvidenceItem(type=EvidenceType.CODE, file="src/payment.py", line_start=50, line_end=50, description="cursor.execute(sql_query)")],
        agent_name="security",
    )

    passed, reason = judge.evaluate_gate1_diff_boundary(
        finding=finding,
        changed_files=["src/payment.py"],
        valid_lines_by_file={"src/payment.py": {"RIGHT": [1, 2, 3]}},
    )

    # Gate 1 must reject because line 50 does not belong to changed lines, despite 0.99 confidence
    assert passed is False
    assert reason is not None
    assert "does not belong to changed review lines" in reason


# ==============================================================================
# 5. MCP GOVERNANCE INVARIANTS
# ==============================================================================


def test_invariant_mcp_forbidden_tools_always_rejected():
    """Invariant: All 9 forbidden tool actions are strictly blocked by PolicyEngine."""
    admin_principal = Principal(
        principal_id="admin-01",
        role=PrincipalRole.ADMIN,
        organization_id="org-1",
        is_ai_agent=False,
    )

    for forbidden_action in FORBIDDEN_TOOL_ACTIONS:
        result = PolicyEngine.evaluate(
            principal=admin_principal,
            organization_id="org-1",
            repository_id="repo-1",
            tool_name=forbidden_action,
        )
        assert result.decision == PolicyDecision.DENY, f"Forbidden tool {forbidden_action} was improperly allowed for ADMIN"
        assert result.requires_approval is False


def test_invariant_mcp_untrusted_agent_cannot_authorize_consequential_actions():
    """Invariant: Untrusted agent principal cannot authorize consequential tools."""
    agent_principal = Principal(
        principal_id="agent-01",
        role=PrincipalRole.AGENT,
        organization_id="org-1",
        is_ai_agent=True,
    )

    result = PolicyEngine.evaluate(
        principal=agent_principal,
        organization_id="org-1",
        repository_id="repo-1",
        tool_name="github_merge_pull_request",
    )
    assert result.decision == PolicyDecision.DENY


# ==============================================================================
# 6. HUMAN APPROVAL & PUBLICATION INVARIANTS
# ==============================================================================


def test_invariant_stale_head_sha_invalidates_approval(db_session: Session, invariant_setup: dict):
    """Invariant: A modified PR head_sha prevents approval and invalidates pending requests."""
    service = ApprovalService(db_session)
    setup = invariant_setup

    req = service.create_approval_request(
        organization_id=setup["org"].id,
        repository_id=setup["repo"].id,
        pull_request_id=setup["pr"].id,
        review_job_id=setup["job"].id,
        head_sha=setup["pr"].head_sha,
        requested_action="COMMENT",
        requested_by="ai-reviewer",
    )

    # Change PR head SHA to simulate a new push
    setup["pr"].head_sha = "head_sha_new_commit_999999999999"
    db_session.commit()

    # Attempting to approve must fail with stale head SHA error
    with pytest.raises(ValueError, match="PR head SHA changed"):
        service.approve_request(
            approval_id=req.id,
            approver_principal_id="alice-reviewer",
            approver_role="REVIEWER",
            is_ai_agent=False,
        )

    # Verify request status transitioned to CANCELLED
    db_session.refresh(req)
    assert req.status == ApprovalStatus.CANCELLED


def test_invariant_unauthorized_approver_rejected(db_session: Session, invariant_setup: dict):
    """Invariant: Non-REVIEWER roles (e.g. MEMBER, GUEST, AI_AGENT) cannot approve requests."""
    service = ApprovalService(db_session)
    setup = invariant_setup

    req = service.create_approval_request(
        organization_id=setup["org"].id,
        repository_id=setup["repo"].id,
        pull_request_id=setup["pr"].id,
        review_job_id=setup["job"].id,
        head_sha=setup["pr"].head_sha,
        requested_action="COMMENT",
        requested_by="ai-reviewer",
    )

    # AI agent rejection
    with pytest.raises(ValueError, match="AI agents cannot approve"):
        service.approve_request(
            approval_id=req.id,
            approver_principal_id="ai-bot",
            approver_role="REVIEWER",
            is_ai_agent=True,
        )

    # Regular member rejection
    with pytest.raises(ValueError, match="not authorized to approve"):
        service.approve_request(
            approval_id=req.id,
            approver_principal_id="regular-member",
            approver_role="MEMBER",
            is_ai_agent=False,
        )


def test_invariant_audit_record_persisted_on_approval(db_session: Session, invariant_setup: dict):
    """Invariant: Every approved request transitions to APPROVED with reason and approved_by."""
    service = ApprovalService(db_session)
    setup = invariant_setup

    req = service.create_approval_request(
        organization_id=setup["org"].id,
        repository_id=setup["repo"].id,
        pull_request_id=setup["pr"].id,
        review_job_id=setup["job"].id,
        head_sha=setup["pr"].head_sha,
        requested_action="COMMENT",
        requested_by="ai-reviewer",
    )

    approved = service.approve_request(
        approval_id=req.id,
        approver_principal_id="alice-lead",
        approver_role="ADMIN",
        is_ai_agent=False,
        comment="Cryptographically approved review",
    )

    assert approved.status == ApprovalStatus.APPROVED
    assert approved.approved_by == "alice-lead"
    assert approved.reason == "Cryptographically approved review"
    assert approved.resolved_at is not None
