"""Policy service managing organization review policy configuration."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.org_policy import OrganizationReviewPolicy


class PolicyService:
    """Service managing organization-level AI review publication policies."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def get_or_create_policy(self, organization_id: str) -> OrganizationReviewPolicy:
        """Fetch policy or create conservative defaults."""
        policy = self.db.scalar(
            select(OrganizationReviewPolicy).where(OrganizationReviewPolicy.organization_id == organization_id)
        )
        if not policy:
            policy = OrganizationReviewPolicy(
                organization_id=organization_id,
                auto_publish_advisory=False,
                auto_publish_low=False,
                require_approval_for_high=True,
                require_approval_for_critical=True,
                allow_request_changes=False,
                allow_ai_github_comments=True,
                approval_expiry_minutes=60,
            )
            self.db.add(policy)
            self.db.commit()
            self.db.refresh(policy)
        return policy

    def update_policy(
        self,
        organization_id: str,
        updater_role: str,
        updates: dict[str, Any],
    ) -> OrganizationReviewPolicy:
        """Update organization policy. Only ADMIN role is authorized."""
        if updater_role.upper() != "ADMIN":
            raise PermissionError("Only ADMIN role can configure organization review policies.")

        policy = self.get_or_create_policy(organization_id)
        for k, v in updates.items():
            if hasattr(policy, k) and k not in ("id", "organization_id", "created_at", "updated_at"):
                setattr(policy, k, v)

        self.db.commit()
        self.db.refresh(policy)
        return policy

    @staticmethod
    def to_dict(policy: OrganizationReviewPolicy) -> dict[str, Any]:
        return {
            "auto_publish_advisory": policy.auto_publish_advisory,
            "auto_publish_low": policy.auto_publish_low,
            "require_approval_for_high": policy.require_approval_for_high,
            "require_approval_for_critical": policy.require_approval_for_critical,
            "allow_request_changes": policy.allow_request_changes,
            "allow_ai_github_comments": policy.allow_ai_github_comments,
            "approval_expiry_minutes": policy.approval_expiry_minutes,
        }
