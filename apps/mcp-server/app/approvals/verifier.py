"""Approval Request Verifier enforcing expiration, binding, and human authorship."""

from datetime import UTC, datetime
from typing import Any, NamedTuple


class ApprovalValidationResult(NamedTuple):
    valid: bool
    status: str
    error_message: str | None


class ApprovalVerifier:
    """Validates that a human approval is active, unexpired, and strictly bound to the target commit."""

    @staticmethod
    def validate_approval(
        approval_record: dict[str, Any] | None,
        expected_repository_id: str,
        expected_pr_id: str,
        expected_head_sha: str,
        expected_action: str,
    ) -> ApprovalValidationResult:
        if not approval_record:
            return ApprovalValidationResult(
                valid=False,
                status="MISSING",
                error_message="Approval record is missing or not found.",
            )

        status = approval_record.get("status")
        if status != "APPROVED":
            return ApprovalValidationResult(
                valid=False,
                status=status or "UNKNOWN",
                error_message=f"Approval status is '{status}', not APPROVED.",
            )

        # Verify repository binding
        if approval_record.get("repository_id") != expected_repository_id:
            return ApprovalValidationResult(
                valid=False,
                status="MISMATCH",
                error_message="Approval repository does not match target repository.",
            )

        # Verify PR binding
        if approval_record.get("pull_request_id") != expected_pr_id:
            return ApprovalValidationResult(
                valid=False,
                status="MISMATCH",
                error_message="Approval pull request does not match target PR.",
            )

        # Verify action binding
        if approval_record.get("requested_action") != expected_action:
            return ApprovalValidationResult(
                valid=False,
                status="MISMATCH",
                error_message=f"Approval action is '{approval_record.get('requested_action')}', but target action is '{expected_action}'.",
            )

        # Verify Head SHA binding (stale commit invalidation)
        if approval_record.get("head_sha") != expected_head_sha:
            return ApprovalValidationResult(
                valid=False,
                status="STALE",
                error_message=f"Approval was granted for commit {approval_record.get('head_sha')[:8]}, but PR head is now {expected_head_sha[:8]}. Approval is STALE.",
            )

        # Verify Expiration
        expires_at = approval_record.get("expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                expires_at_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            else:
                expires_at_dt = expires_at
            if datetime.now(UTC) > expires_at_dt:
                return ApprovalValidationResult(
                    valid=False,
                    status="EXPIRED",
                    error_message=f"Approval expired at {expires_at_dt.isoformat()}.",
                )

        # Verify Human Authorship (No AI agent self-approval)
        approved_by = approval_record.get("approved_by") or ""
        if "agent" in approved_by.lower():
            return ApprovalValidationResult(
                valid=False,
                status="INVALID_AUTHOR",
                error_message="AI agents cannot approve their own actions.",
            )

        return ApprovalValidationResult(
            valid=True,
            status="APPROVED",
            error_message=None,
        )
