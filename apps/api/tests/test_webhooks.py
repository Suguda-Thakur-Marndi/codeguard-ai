"""Tests for GitHub webhook ingestion, signature validation, and event handling."""

import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.organization import Organization
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.review_job import ReviewJob, ReviewJobStatus
from tests.conftest import make_webhook_signature


def test_webhook_missing_signature(client: TestClient, sample_pr_payload: dict) -> None:
    """Webhook without signature header must be rejected with 401."""
    body = json.dumps(sample_pr_payload).encode("utf-8")
    response = client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={"X-GitHub-Event": "pull_request", "Content-Type": "application/json"},
    )
    assert response.status_code == 401
    assert "Invalid GitHub webhook signature" in response.json()["detail"]


def test_webhook_invalid_signature(client: TestClient, sample_pr_payload: dict) -> None:
    """Webhook with incorrect signature must be rejected with 401."""
    body = json.dumps(sample_pr_payload).encode("utf-8")
    response = client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=0000000000000000000000000000000000000000000000000000000000000000",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 401


def test_webhook_tampered_body(client: TestClient, sample_pr_payload: dict) -> None:
    """Webhook where body was modified after signature generation must be rejected with 401."""
    body = json.dumps(sample_pr_payload).encode("utf-8")
    sig = make_webhook_signature(body)
    tampered_body = json.dumps({**sample_pr_payload, "extra": "tampered"}).encode("utf-8")

    response = client.post(
        "/api/v1/webhooks/github",
        content=tampered_body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 401


def test_webhook_ping_event(client: TestClient) -> None:
    """GitHub ping event should return 200 with pong message."""
    payload = {"zen": "Keep it logically awesome.", "hook_id": 9999}
    body = json.dumps(payload).encode("utf-8")
    sig = make_webhook_signature(body)

    response = client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["event"] == "ping"
    assert "Pong" in data["message"]


def test_webhook_unsupported_event(client: TestClient) -> None:
    """Non-PR events like 'issues' or 'push' should be ignored with 200 status."""
    payload = {"action": "created", "issue": {"number": 1}}
    body = json.dumps(payload).encode("utf-8")
    sig = make_webhook_signature(body)

    response = client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "issues",
            "X-Hub-Signature-256": sig,
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"


def test_webhook_pull_request_opened(
    client: TestClient, db_session: Session, sample_pr_payload: dict
) -> None:
    """Opened PR event creates Organization, Repository, PR, and ReviewJob."""
    body = json.dumps(sample_pr_payload).encode("utf-8")
    sig = make_webhook_signature(body)

    response = client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
            "X-GitHub-Delivery": "test-delivery-opened-01",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "accepted"
    assert data["action"] == "opened"
    assert data["review_job_id"] is not None

    # Verify database persistence
    org = db_session.query(Organization).filter_by(github_installation_id=123456).first()
    assert org is not None
    assert org.github_account_login == "acme"

    repo = db_session.query(Repository).filter_by(github_repo_id=998877).first()
    assert repo is not None
    assert repo.full_name == "acme/core-engine"
    assert repo.organization_id == org.id

    pr = db_session.query(PullRequest).filter_by(repository_id=repo.id, number=101).first()
    assert pr is not None
    assert pr.title == "Fix memory leak in buffer pool"
    assert pr.author_login == "octocat"
    assert pr.head_sha == "2222222222222222222222222222222222222222"

    job = db_session.query(ReviewJob).filter_by(id=data["review_job_id"]).first()
    assert job is not None
    assert job.pull_request_id == pr.id
    assert job.status == ReviewJobStatus.PENDING
    assert job.trigger == "webhook:opened"


def test_webhook_duplicate_protection(
    client: TestClient, db_session: Session, sample_pr_payload: dict
) -> None:
    """Duplicate delivery of PR opened webhook must NOT create a second review job."""
    body = json.dumps(sample_pr_payload).encode("utf-8")
    sig = make_webhook_signature(body)

    # 1. First webhook
    res1 = client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
            "X-GitHub-Delivery": "delivery-1",
            "Content-Type": "application/json",
        },
    )
    assert res1.status_code == 202
    job_id_1 = res1.json()["review_job_id"]

    # 2. Duplicate webhook delivery
    res2 = client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": sig,
            "X-GitHub-Delivery": "delivery-2-duplicate",
            "Content-Type": "application/json",
        },
    )
    assert res2.status_code == 200
    assert res2.json()["status"] == "ignored"
    assert res2.json()["review_job_id"] == job_id_1
    assert "already exists" in res2.json()["message"]

    # Assert only 1 review job in database
    jobs_count = db_session.query(ReviewJob).count()
    assert jobs_count == 1


def test_webhook_pull_request_closed(
    client: TestClient, db_session: Session, sample_pr_payload: dict
) -> None:
    """Closed PR event must update PR state to closed and NOT queue a review job."""
    # First create PR
    open_body = json.dumps(sample_pr_payload).encode("utf-8")
    client.post(
        "/api/v1/webhooks/github",
        content=open_body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": make_webhook_signature(open_body),
            "Content-Type": "application/json",
        },
    )

    # Now send closed event
    closed_payload = {**sample_pr_payload, "action": "closed"}
    closed_payload["pull_request"]["state"] = "closed"
    closed_body = json.dumps(closed_payload).encode("utf-8")

    res = client.post(
        "/api/v1/webhooks/github",
        content=closed_body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": make_webhook_signature(closed_body),
            "Content-Type": "application/json",
        },
    )
    assert res.status_code == 200
    assert res.json()["status"] == "ignored"
    assert res.json()["action"] == "closed"

    # Verify PR state is now closed in DB
    pr = db_session.query(PullRequest).filter_by(number=101).first()
    assert pr.state == "closed"


def test_webhook_pull_request_synchronize(
    client: TestClient, db_session: Session, sample_pr_payload: dict
) -> None:
    """Synchronize PR event updates head SHA and queues a new review job."""
    # First open PR
    open_body = json.dumps(sample_pr_payload).encode("utf-8")
    client.post(
        "/api/v1/webhooks/github",
        content=open_body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": make_webhook_signature(open_body),
            "Content-Type": "application/json",
        },
    )

    # Now send synchronize event with new commit
    sync_payload = {**sample_pr_payload, "action": "synchronize"}
    sync_payload["pull_request"]["head"]["sha"] = "3333333333333333333333333333333333333333"
    sync_body = json.dumps(sync_payload).encode("utf-8")

    # Mark prior job as completed so idempotency allows new commit job
    prior_job = db_session.query(ReviewJob).first()
    prior_job.status = ReviewJobStatus.COMPLETED
    db_session.commit()

    response = client.post(
        "/api/v1/webhooks/github",
        content=sync_body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": make_webhook_signature(sync_body),
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 202
    assert response.json()["status"] == "accepted"
    assert response.json()["action"] == "synchronize"

    pr = db_session.query(PullRequest).filter_by(number=101).first()
    assert pr.head_sha == "3333333333333333333333333333333333333333"


def test_webhook_pull_request_reopened(
    client: TestClient, db_session: Session, sample_pr_payload: dict
) -> None:
    """Reopened PR event updates state to open and creates review job."""
    # First open and close
    open_body = json.dumps(sample_pr_payload).encode("utf-8")
    client.post(
        "/api/v1/webhooks/github",
        content=open_body,
        headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": make_webhook_signature(open_body)},
    )
    prior_job = db_session.query(ReviewJob).first()
    prior_job.status = ReviewJobStatus.COMPLETED
    db_session.commit()

    # Send reopened
    reopened_payload = {**sample_pr_payload, "action": "reopened"}
    reopened_body = json.dumps(reopened_payload).encode("utf-8")
    response = client.post(
        "/api/v1/webhooks/github",
        content=reopened_body,
        headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": make_webhook_signature(reopened_body)},
    )
    assert response.status_code == 202
    assert response.json()["action"] == "reopened"


def test_webhook_pull_request_ready_for_review(
    client: TestClient, db_session: Session, sample_pr_payload: dict
) -> None:
    """Ready_for_review event changes draft status to False and queues review job."""
    draft_payload = {**sample_pr_payload, "action": "opened"}
    draft_payload["pull_request"]["draft"] = True
    draft_body = json.dumps(draft_payload).encode("utf-8")
    client.post(
        "/api/v1/webhooks/github",
        content=draft_body,
        headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": make_webhook_signature(draft_body)},
    )

    prior_job = db_session.query(ReviewJob).first()
    if prior_job:
        prior_job.status = ReviewJobStatus.COMPLETED
        db_session.commit()

    # Now ready_for_review
    ready_payload = {**sample_pr_payload, "action": "ready_for_review"}
    ready_payload["pull_request"]["draft"] = False
    ready_body = json.dumps(ready_payload).encode("utf-8")
    response = client.post(
        "/api/v1/webhooks/github",
        content=ready_body,
        headers={"X-GitHub-Event": "pull_request", "X-Hub-Signature-256": make_webhook_signature(ready_body)},
    )
    assert response.status_code == 202
    assert response.json()["action"] == "ready_for_review"

    pr = db_session.query(PullRequest).filter_by(number=101).first()
    assert pr.is_draft is False


def test_webhook_draft_pr_ignored_when_configured(
    client: TestClient, sample_pr_payload: dict, monkeypatch
) -> None:
    """Draft PRs should be ignored when IGNORE_DRAFT_PRS is enabled."""
    monkeypatch.setattr(settings, "IGNORE_DRAFT_PRS", True)
    draft_payload = {**sample_pr_payload, "action": "opened"}
    draft_payload["pull_request"]["draft"] = True
    body = json.dumps(draft_payload).encode("utf-8")

    response = client.post(
        "/api/v1/webhooks/github",
        content=body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": make_webhook_signature(body),
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert "Draft pull requests are ignored" in response.json()["message"]
