"""Unit tests for PolicyEngine and zero-trust boundary verification."""

from datetime import UTC, datetime, timedelta

import pytest

from app.auth.service_auth import Principal, PrincipalRole
from app.policies.policy_engine import PolicyDecision, PolicyEngine
from app.schemas.tools import ToolRiskLevel


@pytest.fixture
def agent_principal() -> Principal:
    return Principal(
        principal_id="gemini-agent-1",
        role=PrincipalRole.AGENT,
        organization_id="org-1",
        is_ai_agent=True,
    )


@pytest.fixture
def human_reviewer_principal() -> Principal:
    return Principal(
        principal_id="alice-reviewer",
        role=PrincipalRole.REVIEWER,
        organization_id="org-1",
        is_ai_agent=False,
    )


def test_forbidden_action_denied(agent_principal: Principal) -> None:
    res = PolicyEngine.evaluate(
        principal=agent_principal,
        organization_id="org-1",
        repository_id="repo-1",
        tool_name="merge_pull_request",
        parameters={},
    )
    assert res.decision == PolicyDecision.DENY
    assert "strictly forbidden" in res.reason


def test_read_only_allowed(agent_principal: Principal) -> None:
    res = PolicyEngine.evaluate(
        principal=agent_principal,
        organization_id="org-1",
        repository_id="repo-1",
        tool_name="get_file",
        parameters={"file_path": "main.py"},
    )
    assert res.decision == PolicyDecision.ALLOW
    assert res.risk_level == ToolRiskLevel.READ_ONLY


def test_submit_review_unapproved_requires_approval(agent_principal: Principal) -> None:
    res = PolicyEngine.evaluate(
        principal=agent_principal,
        organization_id="org-1",
        repository_id="repo-1",
        tool_name="submit_review",
        parameters={"action": "COMMENT", "head_sha": "abc1234"},
        org_policy={"require_approval_for_high": True},
        findings_metadata=[{"id": "f1", "status": "PUBLISHABLE", "final_severity": "HIGH"}],
        approval_record=None,
    )
    assert res.decision == PolicyDecision.REQUIRE_APPROVAL
    assert res.requires_approval is True


def test_submit_review_with_valid_human_approval(agent_principal: Principal) -> None:
    approval = {
        "id": "appr-1",
        "status": "APPROVED",
        "head_sha": "abc1234",
        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        "approved_by": "alice-reviewer",
    }
    res = PolicyEngine.evaluate(
        principal=agent_principal,
        organization_id="org-1",
        repository_id="repo-1",
        tool_name="submit_review",
        parameters={"action": "COMMENT", "head_sha": "abc1234"},
        org_policy={"require_approval_for_high": True},
        findings_metadata=[{"id": "f1", "status": "PUBLISHABLE", "final_severity": "HIGH"}],
        approval_record=approval,
    )
    assert res.decision == PolicyDecision.ALLOW


def test_submit_review_stale_sha_denied(agent_principal: Principal) -> None:
    # Approval was for sha-old, but PR head is sha-new
    approval = {
        "id": "appr-1",
        "status": "APPROVED",
        "head_sha": "sha-old",
        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        "approved_by": "alice-reviewer",
    }
    res = PolicyEngine.evaluate(
        principal=agent_principal,
        organization_id="org-1",
        repository_id="repo-1",
        tool_name="submit_review",
        parameters={"action": "COMMENT", "head_sha": "sha-new"},
        org_policy={"require_approval_for_high": True},
        findings_metadata=[{"id": "f1", "status": "PUBLISHABLE", "final_severity": "HIGH"}],
        approval_record=approval,
    )
    assert res.decision == PolicyDecision.DENY
    assert "STALE" in res.reason


def test_submit_review_ai_self_approval_denied(agent_principal: Principal) -> None:
    # Attempted self-approval by agent
    approval = {
        "id": "appr-1",
        "status": "APPROVED",
        "head_sha": "abc1234",
        "expires_at": (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
        "approved_by": "gemini-agent-1",
    }
    res = PolicyEngine.evaluate(
        principal=agent_principal,
        organization_id="org-1",
        repository_id="repo-1",
        tool_name="submit_review",
        parameters={"action": "COMMENT", "head_sha": "abc1234"},
        org_policy={"require_approval_for_high": True},
        findings_metadata=[{"id": "f1", "status": "PUBLISHABLE", "final_severity": "HIGH"}],
        approval_record=approval,
    )
    assert res.decision == PolicyDecision.DENY
    assert "AI agents cannot approve their own actions" in res.reason
