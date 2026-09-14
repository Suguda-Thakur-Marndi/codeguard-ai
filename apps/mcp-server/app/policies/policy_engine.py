"""Deterministic Tool Authorization Policy Engine."""

from datetime import UTC, datetime
from typing import Any, NamedTuple

from app.auth.service_auth import Principal
from app.policies.classification import FORBIDDEN_TOOL_ACTIONS, TOOL_RISK_MAP
from app.schemas.tools import PolicyDecision, ToolRiskLevel


class AuthorizationResult(NamedTuple):
    decision: PolicyDecision
    reason: str
    risk_level: ToolRiskLevel
    requires_approval: bool


class PolicyEngine:
    """
    Deterministic authorization engine enforcing zero-trust boundaries over AI agent tool access.
    The LLM is untrusted. Authorization is strictly decided by application code.
    """

    @classmethod
    def evaluate(
        cls,
        principal: Principal,
        organization_id: str,
        repository_id: str | None,
        tool_name: str,
        parameters: dict[str, Any],
        org_policy: dict[str, Any] | None = None,
        approval_record: dict[str, Any] | None = None,
        findings_metadata: list[dict[str, Any]] | None = None,
    ) -> AuthorizationResult:
        # 1. Reject forbidden actions immediately
        if tool_name in FORBIDDEN_TOOL_ACTIONS:
            return AuthorizationResult(
                decision=PolicyDecision.DENY,
                reason=FORBIDDEN_TOOL_ACTIONS[tool_name],
                risk_level=ToolRiskLevel.HIGH_RISK,
                requires_approval=False,
            )

        # 2. Lookup registered risk level
        risk_level = TOOL_RISK_MAP.get(tool_name)
        if risk_level is None:
            return AuthorizationResult(
                decision=PolicyDecision.DENY,
                reason=f"Tool '{tool_name}' is not registered in the MCP Tool Registry.",
                risk_level=ToolRiskLevel.HIGH_RISK,
                requires_approval=False,
            )

        # 3. Read-only operations are universally safe for authenticated callers
        if risk_level == ToolRiskLevel.READ_ONLY:
            return AuthorizationResult(
                decision=PolicyDecision.ALLOW,
                reason="Read-only tool access permitted for authenticated principal.",
                risk_level=ToolRiskLevel.READ_ONLY,
                requires_approval=False,
            )

        # 4. Low-risk operations (sandboxed validation)
        if tool_name == "run_validation":
            return AuthorizationResult(
                decision=PolicyDecision.ALLOW,
                reason="Validation execution in isolated sandbox permitted.",
                risk_level=ToolRiskLevel.LOW_RISK,
                requires_approval=False,
            )

        # 5. Consequential / High-risk operation: submit_review
        if tool_name == "submit_review":
            return cls._evaluate_submit_review(
                principal=principal,
                organization_id=organization_id,
                repository_id=repository_id,
                parameters=parameters,
                org_policy=org_policy or {},
                approval_record=approval_record,
                findings_metadata=findings_metadata or [],
            )

        # Default fallback: Deny unknown or unhandled tools
        return AuthorizationResult(
            decision=PolicyDecision.DENY,
            reason=f"No authorization policy configured for tool '{tool_name}'.",
            risk_level=risk_level,
            requires_approval=False,
        )

    @classmethod
    def _evaluate_submit_review(
        cls,
        principal: Principal,
        organization_id: str,
        repository_id: str | None,
        parameters: dict[str, Any],
        org_policy: dict[str, Any],
        approval_record: dict[str, Any] | None,
        findings_metadata: list[dict[str, Any]],
    ) -> AuthorizationResult:
        action = parameters.get("action", "COMMENT")
        head_sha = parameters.get("head_sha", "")

        # A. Check Organization baseline permissions
        allow_ai_comments = org_policy.get("allow_ai_github_comments", True)
        if not allow_ai_comments:
            return AuthorizationResult(
                decision=PolicyDecision.DENY,
                reason="Organization policy has disabled all automated AI GitHub comments.",
                risk_level=ToolRiskLevel.CONSEQUENTIAL,
                requires_approval=False,
            )

        allow_request_changes = org_policy.get("allow_request_changes", False)
        if action == "REQUEST_CHANGES" and not allow_request_changes:
            return AuthorizationResult(
                decision=PolicyDecision.DENY,
                reason="Organization policy forbids AI agents from submitting REQUEST_CHANGES reviews.",
                risk_level=ToolRiskLevel.HIGH_RISK,
                requires_approval=False,
            )

        # B. Verify finding status integrity: Only PUBLISHABLE findings can be published
        for f in findings_metadata:
            status = f.get("status", "")
            if status not in ("PUBLISHABLE", "PUBLISHED"):
                return AuthorizationResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Finding '{f.get('id')}' is in status '{status}'. Only PUBLISHABLE findings can be published.",
                    risk_level=ToolRiskLevel.CONSEQUENTIAL,
                    requires_approval=False,
                )

        # C. Determine whether human approval is required
        requires_approval = False
        severities = {f.get("final_severity") or f.get("severity") for f in findings_metadata}

        if action == "REQUEST_CHANGES" or "CRITICAL" in severities and org_policy.get("require_approval_for_critical", True) or "HIGH" in severities and org_policy.get("require_approval_for_high", True) or "MEDIUM" in severities or "LOW" in severities and not org_policy.get("auto_publish_low", False) or "ADVISORY" in severities and not org_policy.get("auto_publish_advisory", False):
            requires_approval = True

        effective_risk = ToolRiskLevel.HIGH_RISK if action == "REQUEST_CHANGES" else ToolRiskLevel.CONSEQUENTIAL

        # If approval is NOT required by policy, allow publication immediately
        if not requires_approval:
            return AuthorizationResult(
                decision=PolicyDecision.ALLOW,
                reason="Review publication allowed by policy (auto-publish enabled for low/advisory findings).",
                risk_level=effective_risk,
                requires_approval=False,
            )

        # D. Approval IS required: Validate attached approval record
        if not approval_record:
            return AuthorizationResult(
                decision=PolicyDecision.REQUIRE_APPROVAL,
                reason=f"Action '{action}' with findings {list(severities)} requires human reviewer approval.",
                risk_level=effective_risk,
                requires_approval=True,
            )

        # 1. Verify approval status
        if approval_record.get("status") != "APPROVED":
            return AuthorizationResult(
                decision=PolicyDecision.DENY,
                reason=f"Approval request '{approval_record.get('id')}' is in status '{approval_record.get('status')}', not APPROVED.",
                risk_level=effective_risk,
                requires_approval=True,
            )

        # 2. Verify head SHA match (Binding to exact commit)
        if approval_record.get("head_sha") != head_sha:
            return AuthorizationResult(
                decision=PolicyDecision.DENY,
                reason=f"Approval is bound to head SHA {approval_record.get('head_sha')[:8]}, but current PR head SHA is {head_sha[:8]}. Approval is STALE.",
                risk_level=effective_risk,
                requires_approval=True,
            )

        # 3. Verify approval expiration
        expires_at = approval_record.get("expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                expires_at_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            else:
                expires_at_dt = expires_at
            if datetime.now(UTC) > expires_at_dt:
                return AuthorizationResult(
                    decision=PolicyDecision.DENY,
                    reason=f"Approval request '{approval_record.get('id')}' has expired.",
                    risk_level=effective_risk,
                    requires_approval=True,
                )

        # 4. Verify approver principal is not an AI Agent (No AI self-approval!)
        approver = approval_record.get("approved_by") or ""
        if "agent" in approver.lower() or approver == principal.principal_id and principal.is_ai_agent:
            return AuthorizationResult(
                decision=PolicyDecision.DENY,
                reason="AI agents cannot approve their own actions. An authorized human reviewer is required.",
                risk_level=effective_risk,
                requires_approval=True,
            )

        # All checks passed for approved request!
        return AuthorizationResult(
            decision=PolicyDecision.ALLOW,
            reason=f"Action authorized by verified human approval '{approval_record.get('id')}'.",
            risk_level=effective_risk,
            requires_approval=False,
        )
