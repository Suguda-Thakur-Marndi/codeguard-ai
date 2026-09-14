"""Webhook processing and ingestion service."""

from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import WebhookVerificationError
from app.core.logging import TimingLogger, logger
from app.core.security import verify_github_signature
from app.db.repositories.organization_repo import OrganizationRepository
from app.db.repositories.pull_request_repo import PullRequestRepository
from app.db.repositories.repository_repo import RepositoryRepository
from app.db.repositories.review_job_repo import ReviewJobRepository
from app.schemas.webhook import GitHubWebhookPayload, WebhookResponse


class WebhookService:
    """Orchestrates GitHub webhook verification, entity upserts, and job creation."""

    SUPPORTED_PR_ACTIONS = {
        "opened",
        "synchronize",
        "reopened",
        "ready_for_review",
    }

    def __init__(self, db: Session):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.repo_repo = RepositoryRepository(db)
        self.pr_repo = PullRequestRepository(db)
        self.job_repo = ReviewJobRepository(db)

    def verify_payload(self, raw_body: bytes, signature_header: str | None) -> None:
        """Enforce HMAC-SHA256 signature verification."""
        if not verify_github_signature(raw_body, signature_header):
            logger.warning("Rejected webhook: invalid signature")
            raise WebhookVerificationError()
        logger.debug("GitHub webhook signature verified successfully")

    def process_webhook(
        self,
        event_type: str,
        delivery_id: str,
        payload_data: dict[str, Any],
    ) -> WebhookResponse:
        """Process verified GitHub webhook payload and enqueue review job if applicable."""
        with TimingLogger("webhook_received", {"event": event_type, "delivery_id": delivery_id}):
            logger.info(
                f"Processing webhook event: {event_type}",
                extra={
                    "event": "webhook_received",
                    "extra_fields": {"delivery_id": delivery_id, "event_type": event_type},
                },
            )

            # Handle ping event
            if event_type == "ping":
                return WebhookResponse(
                    status="success",
                    event="ping",
                    message="Pong! Webhook verified successfully.",
                )

            # Ignore non-PR events for review job creation in Phase 1
            if event_type != "pull_request":
                return WebhookResponse(
                    status="ignored",
                    event=event_type,
                    message=f"Event '{event_type}' is not monitored for review jobs in Phase 1.",
                )

            payload = GitHubWebhookPayload.model_validate(payload_data)
            action = payload.action or "unknown"

            # Check if action is handled
            if action not in self.SUPPORTED_PR_ACTIONS:
                # If closed, still update PR state in database
                if action == "closed" and payload.pull_request and payload.repository:
                    self._update_pr_state(payload, "closed")
                return WebhookResponse(
                    status="ignored",
                    event="pull_request",
                    action=action,
                    message=f"Action '{action}' does not trigger a review job.",
                )

            if not payload.pull_request or not payload.repository:
                return WebhookResponse(
                    status="error",
                    event="pull_request",
                    action=action,
                    message="Missing pull_request or repository payload data.",
                )

            # Check draft status against configuration
            is_draft = payload.pull_request.draft
            if is_draft and settings.IGNORE_DRAFT_PRS:
                logger.info("Skipping review job for draft PR per configuration")
                return WebhookResponse(
                    status="ignored",
                    event="pull_request",
                    action=action,
                    message="Draft pull requests are ignored per configuration.",
                )

            # 1. Find or create Organization
            installation_id = (
                payload.installation.id
                if payload.installation
                else int(settings.GITHUB_APP_ID if settings.GITHUB_APP_ID.isdigit() else 1)
            )
            repo_owner = payload.repository.owner
            org = self.org_repo.get_or_create(
                installation_id=installation_id,
                account_id=repo_owner.id or 1,
                account_login=repo_owner.login,
                account_type=repo_owner.type or "Organization",
            )

            # 2. Find or create Repository
            repo = self.repo_repo.get_or_create(
                organization_id=org.id,
                github_repo_id=payload.repository.id,
                owner=repo_owner.login,
                name=payload.repository.name,
                full_name=payload.repository.full_name,
                default_branch=payload.repository.default_branch,
                is_private=payload.repository.private,
            )

            # 3. Upsert Pull Request
            pr_data = payload.pull_request
            pr = self.pr_repo.upsert_pull_request(
                repository_id=repo.id,
                github_pr_id=pr_data.id,
                number=pr_data.number,
                title=pr_data.title,
                description=pr_data.body,
                author_login=pr_data.user.login,
                base_sha=pr_data.base.sha,
                head_sha=pr_data.head.sha,
                state=pr_data.state,
                is_draft=pr_data.draft,
            )

            logger.info(
                f"Pull Request registered: {repo.full_name}#{pr.number}",
                extra={"event": "pr_discovered", "extra_fields": {"pr_id": pr.id, "head_sha": pr.head_sha}},
            )

            # 4. Idempotency Check: prevent duplicate active jobs for this PR
            active_job = self.job_repo.get_active_job_for_pr(pr.id)
            if active_job:
                logger.info(
                    f"Active review job {active_job.id} already exists for PR {pr.id}. Skipping duplicate.",
                    extra={"event": "review_job_duplicate", "extra_fields": {"job_id": active_job.id}},
                )
                return WebhookResponse(
                    status="ignored",
                    event="pull_request",
                    action=action,
                    review_job_id=active_job.id,
                    message="An active review job already exists for this PR.",
                )

            # 5. Create Review Job
            job = self.job_repo.create_job(
                pull_request_id=pr.id,
                trigger=f"webhook:{action}",
            )

            logger.info(
                f"Review job created: {job.id}",
                extra={"event": "review_job_created", "extra_fields": {"review_job_id": job.id}},
            )

            # 6. Dispatch background task to Celery worker
            self._dispatch_job(job.id)

            return WebhookResponse(
                status="accepted",
                event="pull_request",
                action=action,
                review_job_id=job.id,
                message=f"Review job {job.id} queued successfully.",
            )

    def _update_pr_state(self, payload: GitHubWebhookPayload, state: str) -> None:
        """Update pull request state without creating a review job."""
        if not payload.repository or not payload.pull_request:
            return
        repo = self.repo_repo.get_by_github_repo_id(payload.repository.id)
        if repo:
            pr = self.pr_repo.get_by_repo_and_number(repo.id, payload.pull_request.number)
            if pr:
                pr.state = state
                self.pr_repo.update(pr)

    def _dispatch_job(self, job_id: str) -> None:
        """Enqueue review job in Celery worker or run synchronously if configured."""
        try:
            from app.workers.tasks import process_review_job
            process_review_job.delay(job_id)
            logger.info(f"Dispatched review job {job_id} to background worker")
        except Exception as e:
            logger.error(f"Failed to enqueue Celery task for review job {job_id}: {e}", exc_info=True)
            # In local dev/test fallback without Redis running, execute synchronously if needed
            if settings.CELERY_TASK_ALWAYS_EAGER or settings.APP_ENV in ("test", "development"):
                try:
                    from app.workers.tasks import run_review_job_sync
                    run_review_job_sync(job_id, self.db)
                except Exception as sync_err:
                    logger.error(f"Synchronous fallback job execution failed: {sync_err}")
