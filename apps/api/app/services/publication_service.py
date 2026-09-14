"""Publication service managing atomic GitHub PR review publication and background jobs."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import logger
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.github_publication import (
    GitHubReviewComment,
    GitHubReviewPublication,
    PublicationStatus,
)
from app.models.organization import Organization
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.review_artifact import ArtifactType, ReviewArtifact
from app.models.review_finding import FindingStatus, ReviewFindingModel
from app.models.review_job import ReviewJob
from app.services.approval_service import ApprovalService
from app.services.mcp_client import MCPClient
from app.services.policy_service import PolicyService


class PublicationService:
    """Service managing atomic GitHub review publication through the MCP gateway."""

    def __init__(self, db: Session, mcp_client: MCPClient | None = None) -> None:
        self.db = db
        self.mcp_client = mcp_client or MCPClient()
        self.approval_service = ApprovalService(db)
        self.policy_service = PolicyService(db)

    def prepare_publication(
        self,
        review_job_id: str,
        action: str = "COMMENT",
        requested_by: str = "agent",
    ) -> tuple[GitHubReviewPublication, ApprovalRequest | None]:
        """
        Evaluates policy and prepares publication record.
        Creates an ApprovalRequest if human authorization is required.
        Guarantees idempotency via composite publication key.
        """
        job = self.db.scalar(select(ReviewJob).where(ReviewJob.id == review_job_id))
        if not job:
            raise ValueError(f"ReviewJob '{review_job_id}' not found.")

        pr = self.db.scalar(select(PullRequest).where(PullRequest.id == job.pull_request_id))
        if not pr:
            raise ValueError(f"PullRequest '{job.pull_request_id}' not found.")

        repo = self.db.scalar(select(Repository).where(Repository.id == pr.repository_id))
        if not repo:
            raise ValueError(f"Repository '{pr.repository_id}' not found.")

        org = self.db.scalar(select(Organization).where(Organization.id == repo.organization_id))
        if not org:
            raise ValueError(f"Organization '{repo.organization_id}' not found.")

        # Composite idempotency key: repo:pr:head_sha:job_id
        pub_key = f"{repo.id}:{pr.id}:{pr.head_sha}:{job.id}"
        existing_pub = self.db.scalar(
            select(GitHubReviewPublication).where(GitHubReviewPublication.publication_key == pub_key)
        )
        if existing_pub and existing_pub.status == PublicationStatus.PUBLISHED:
            # Idempotency hit: already published
            return existing_pub, None

        # Fetch all findings eligible for publication (strictly PUBLISHABLE)
        findings = list(
            self.db.scalars(
                select(ReviewFindingModel).where(
                    ReviewFindingModel.review_job_id == job.id,
                    ReviewFindingModel.status == FindingStatus.PUBLISHABLE,
                )
            ).all()
        )

        findings_meta = [
            {
                "id": f.id,
                "status": f.status.value,
                "severity": f.severity.value,
                "final_severity": f.final_severity or f.severity.value,
                "file_path": f.file_path,
                "line_number": f.line_number,
                "title": f.title,
                "category": f.category.value,
            }
            for f in findings
        ]

        # Evaluate organization policy
        policy = self.policy_service.get_or_create_policy(org.id)
        org_policy_dict = PolicyService.to_dict(policy)

        # Check existing approval request for this review job & head SHA
        approval_req = self.db.scalar(
            select(ApprovalRequest).where(
                ApprovalRequest.review_job_id == job.id,
                ApprovalRequest.head_sha == pr.head_sha,
                ApprovalRequest.status.in_((ApprovalStatus.PENDING, ApprovalStatus.APPROVED)),
            ).order_by(ApprovalRequest.created_at.desc())
        )

        approval_record = None
        if approval_req:
            approval_record = {
                "id": approval_req.id,
                "status": approval_req.status.value,
                "head_sha": approval_req.head_sha,
                "expires_at": approval_req.expires_at.isoformat(),
                "approved_by": approval_req.approved_by,
                "repository_id": approval_req.repository_id,
                "pull_request_id": approval_req.pull_request_id,
                "requested_action": approval_req.requested_action,
            }

        # Query MCP policy evaluation
        from app.mcp.auth import Principal, PrincipalRole
        from app.mcp.policy_engine import PolicyDecision, PolicyEngine

        agent_principal = Principal(
            principal_id=requested_by,
            role=PrincipalRole.AGENT,
            organization_id=org.id,
            is_ai_agent=True,
        )

        authz = PolicyEngine.evaluate(
            principal=agent_principal,
            organization_id=org.id,
            repository_id=repo.id,
            tool_name="submit_review",
            parameters={"action": action, "head_sha": pr.head_sha},
            org_policy=org_policy_dict,
            approval_record=approval_record,
            findings_metadata=findings_meta,
        )

        # Ensure publication record exists
        if not existing_pub:
            existing_pub = GitHubReviewPublication(
                review_job_id=job.id,
                repository_id=repo.id,
                pull_request_id=pr.id,
                head_sha=pr.head_sha,
                event=action,
                status=PublicationStatus.PENDING,
                publication_key=pub_key,
            )
            self.db.add(existing_pub)
            self.db.commit()
            self.db.refresh(existing_pub)

        # If policy requires human approval
        if authz.decision == PolicyDecision.REQUIRE_APPROVAL:
            if not approval_req:
                approval_req = self.approval_service.create_approval_request(
                    organization_id=org.id,
                    repository_id=repo.id,
                    pull_request_id=pr.id,
                    review_job_id=job.id,
                    head_sha=pr.head_sha,
                    requested_action=action,
                    risk_level=authz.risk_level.value,
                    requested_by=requested_by,
                    expiry_minutes=policy.approval_expiry_minutes,
                )
            existing_pub.status = PublicationStatus.APPROVAL_REQUIRED
            self.db.commit()
            return existing_pub, approval_req

        # If allowed, ready to publish
        existing_pub.status = PublicationStatus.PENDING
        self.db.commit()
        return existing_pub, approval_req

    async def execute_publication(
        self,
        publication_id: str,
        current_head_sha_override: str | None = None,
        publisher: Any = None,
    ) -> GitHubReviewPublication:
        """
        Executes publication through the MCP gateway:
        1. Checks Head SHA freshness (Stale SHA aborts).
        2. Verifies line boundaries against diff hunks.
        3. Enforces idempotency: if already PUBLISHED, returns immediately.
        4. Invokes MCP submit_review tool.
        5. Persists GitHub identifiers and updates finding statuses to PUBLISHED.
        """
        pub = self.db.scalar(select(GitHubReviewPublication).where(GitHubReviewPublication.id == publication_id))
        if not pub:
            raise ValueError(f"Publication '{publication_id}' not found.")

        # Idempotency check: Already published returns immediately
        if pub.status == PublicationStatus.PUBLISHED:
            logger.info(f"Publication '{publication_id}' is already PUBLISHED. Returning idempotent result.")
            return pub

        if pub.status == PublicationStatus.STALE:
            raise ValueError(f"Publication '{publication_id}' is STALE and cannot be published.")

        pr = self.db.scalar(select(PullRequest).where(PullRequest.id == pub.pull_request_id))
        if not pr:
            raise ValueError("PullRequest not found.")

        repo = self.db.scalar(select(Repository).where(Repository.id == pub.repository_id))
        if not repo:
            raise ValueError("Repository not found.")

        # Stale Head SHA check: PR HEAD must match verified commit
        effective_current_sha = current_head_sha_override or pr.head_sha
        if effective_current_sha != pub.head_sha:
            pub.status = PublicationStatus.STALE
            pub.error_message = f"PR HEAD has moved from {pub.head_sha[:8]} to {effective_current_sha[:8]}. Review is STALE."
            self.db.commit()
            raise ValueError(pub.error_message)

        # Check approval if required
        approval_req = self.db.scalar(
            select(ApprovalRequest).where(
                ApprovalRequest.review_job_id == pub.review_job_id,
                ApprovalRequest.head_sha == pub.head_sha,
                ApprovalRequest.status == ApprovalStatus.APPROVED,
            )
        )

        approval_record = None
        if approval_req:
            approval_record = {
                "id": approval_req.id,
                "status": approval_req.status.value,
                "head_sha": approval_req.head_sha,
                "expires_at": approval_req.expires_at.isoformat(),
                "approved_by": approval_req.approved_by,
                "repository_id": approval_req.repository_id,
                "pull_request_id": approval_req.pull_request_id,
                "requested_action": approval_req.requested_action,
            }

        # Gather publishable findings
        findings = list(
            self.db.scalars(
                select(ReviewFindingModel).where(
                    ReviewFindingModel.review_job_id == pub.review_job_id,
                    ReviewFindingModel.status == FindingStatus.PUBLISHABLE,
                )
            ).all()
        )

        findings_data = [
            {
                "id": f.id,
                "status": f.status.value,
                "severity": f.severity.value,
                "final_severity": f.final_severity or f.severity.value,
                "file_path": f.file_path,
                "line_number": f.line_number,
                "side": f.side,
                "title": f.title,
                "description": f.description,
                "impact": f.impact,
                "recommendation": f.recommendation,
                "category": f.category.value,
            }
            for f in findings
        ]

        # Retrieve valid diff lines from CHANGED_LINE_INDEX artifact
        line_idx_art = self.db.scalar(
            select(ReviewArtifact).where(
                ReviewArtifact.review_job_id == pub.review_job_id,
                ReviewArtifact.artifact_type == ArtifactType.CHANGED_LINE_INDEX,
            )
        )
        valid_lines_by_file = line_idx_art.metadata_json if line_idx_art and line_idx_art.metadata_json else None

        # Build context for MCP submit_review tool
        context = {
            "findings": findings_data,
            "valid_lines_by_file": valid_lines_by_file,
            "current_head_sha": effective_current_sha,
            "owner": repo.full_name.split("/")[0] if "/" in repo.full_name else "org",
            "repo": repo.name,
            "publisher": publisher,
        }

        # Mark PUBLISHING
        pub.status = PublicationStatus.PUBLISHING
        self.db.commit()

        # Execute submit_review tool via MCP Client
        org_policy = PolicyService.to_dict(self.policy_service.get_or_create_policy(repo.organization_id))

        mcp_res = await self.mcp_client.execute_tool(
            tool_name="submit_review",
            parameters={
                "repository_id": repo.id,
                "pull_request_number": pr.number,
                "head_sha": pub.head_sha,
                "review_job_id": pub.review_job_id,
                "action": pub.event,
                "approval_id": approval_req.id if approval_req else None,
            },
            organization_id=repo.organization_id,
            principal_id="publication-worker",
            principal_role="SERVICE",
            is_ai_agent=False,
            repository_id=repo.id,
            org_policy=org_policy,
            approval_record=approval_record,
            findings_metadata=findings_data,
            context=context,
        )

        if not mcp_res.get("success"):
            err_data = mcp_res.get("error", {})
            err_msg = err_data.get("message", "MCP review publication rejected.")
            pub.status = PublicationStatus.STALE if "STALE" in err_msg else PublicationStatus.FAILED
            pub.error_message = err_msg
            self.db.commit()
            raise RuntimeError(f"Review publication failed: {err_msg}")

        # Success! Persist GitHub review and inline comment records
        result_data = mcp_res.get("data", {})
        pub.github_review_id = result_data.get("github_review_id")
        pub.comment_count = result_data.get("comment_count", len(findings))
        pub.published_at = datetime.now(UTC)
        pub.status = PublicationStatus.PUBLISHED
        pub.error_message = None

        created_comment_ids = result_data.get("created_comment_ids", [])
        for i, finding in enumerate(findings):
            gh_comment_id = created_comment_ids[i] if i < len(created_comment_ids) else None
            comment_record = GitHubReviewComment(
                publication_id=pub.id,
                finding_id=finding.id,
                github_comment_id=gh_comment_id,
                file_path=finding.file_path,
                line_number=finding.line_number,
                side=finding.side,
                body=f"[{finding.severity.value}] {finding.title}",
                status="PUBLISHED",
            )
            self.db.add(comment_record)
            # Update finding status to PUBLISHED
            finding.status = FindingStatus.PUBLISHED

        self.db.commit()
        self.db.refresh(pub)
        return pub
