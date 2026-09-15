"""End-to-end local production-readiness verification script for CodeGuard AI (Phase 1)."""

import hashlib
import hmac
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "apps", "api")))
os.environ["APP_ENV"] = "development"
os.environ["DATABASE_URL"] = "sqlite:///local_verify.db"
os.environ["CELERY_TASK_ALWAYS_EAGER"] = "true"

from app.core.config import settings
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app
from app.workers.tasks import run_review_job_sync
from fastapi.testclient import TestClient


def log_step(name: str):
    print(f"\n[PHASE 1 VERIFY] ---> {name}")


def main():
    print("==================================================================")
    print("       CODEGUARD AI — PHASE 1 END-TO-END VERIFICATION             ")
    print("==================================================================")

    # 1. Initialize SQLite local test database schema
    log_step("1. Initializing Database Schema")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("   Database schema created successfully.")

    client = TestClient(app)

    # 2. Health & Readiness probes
    log_step("2. Testing Health & Readiness Probes")
    health_res = client.get("/api/v1/health")
    assert health_res.status_code == 200, f"Health check failed: {health_res.text}"
    print(f"   Health check: {health_res.json()}")

    ready_res = client.get("/api/v1/ready")
    print(f"   Readiness check: status={ready_res.status_code} payload={ready_res.json()}")

    # 3. Webhook signature rejection test
    log_step("3. Testing Webhook Signature Verification")
    payload = {
        "action": "opened",
        "number": 42,
        "pull_request": {
            "id": 88776655,
            "number": 42,
            "title": "Fix memory leak in buffer pool",
            "body": "Resolves issue where buffer was not dereferenced.",
            "state": "open",
            "draft": False,
            "user": {"login": "octocat"},
            "base": {"sha": "1111111111111111111111111111111111111111"},
            "head": {"sha": "2222222222222222222222222222222222222222"},
        },
        "repository": {
            "id": 123456,
            "name": "core-engine",
            "full_name": "acme-corp/core-engine",
            "private": True,
            "default_branch": "main",
            "owner": {"id": 999, "login": "acme-corp", "type": "Organization"},
        },
        "installation": {"id": 1001},
    }
    raw_body = json.dumps(payload).encode("utf-8")

    # Bad signature
    bad_res = client.post(
        "/api/v1/webhooks/github",
        content=raw_body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": "sha256=invalid_hex_signature",
            "Content-Type": "application/json",
        },
    )
    assert bad_res.status_code == 401, f"Expected 401 on bad signature, got {bad_res.status_code}"
    print("   Bad signature properly rejected with HTTP 401 Unauthorized.")

    # Valid HMAC SHA-256 signature
    mac = hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    )
    valid_sig = f"sha256={mac.hexdigest()}"

    # 4. Webhook Ingestion
    log_step("4. Ingesting Real GitHub Pull Request Webhook")
    webhook_res = client.post(
        "/api/v1/webhooks/github",
        content=raw_body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": valid_sig,
            "X-GitHub-Delivery": "delivery-e2e-001",
            "Content-Type": "application/json",
        },
    )
    assert webhook_res.status_code in (200, 202), f"Webhook failed: {webhook_res.text}"
    webhook_data = webhook_res.json()
    job_id = webhook_data["review_job_id"]
    print(f"   Webhook accepted: status={webhook_data['status']}, review_job_id={job_id}")

    # 5. Duplicate Webhook Protection Check
    log_step("5. Testing Duplicate Webhook Delivery Protection")
    dup_res = client.post(
        "/api/v1/webhooks/github",
        content=raw_body,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": valid_sig,
            "X-GitHub-Delivery": "delivery-e2e-002-dup",
            "Content-Type": "application/json",
        },
    )
    assert dup_res.status_code == 200, f"Expected 200 on duplicate, got {dup_res.status_code}"
    dup_data = dup_res.json()
    assert dup_data["status"] == "ignored", f"Duplicate was not ignored: {dup_data}"
    assert dup_data["review_job_id"] == job_id
    print("   Duplicate webhook delivery successfully intercepted without creating a duplicate job.")

    # 6. Worker Execution Simulation
    log_step("6. Executing Background Review Job Worker")
    db = SessionLocal()
    try:
        worker_result = run_review_job_sync(job_id, db)
        print(f"   Worker execution result: {worker_result}")
        assert worker_result["status"] == "success"
        assert worker_result["job_status"] == "COMPLETED"
    finally:
        db.close()

    # 7. Query REST APIs for persisted entities & artifacts
    log_step("7. Verifying REST API Collection & Detail Endpoints")
    # Organizations
    orgs_res = client.get("/api/v1/organizations")
    assert orgs_res.status_code == 200
    assert len(orgs_res.json()["items"]) >= 1
    print(f"   GET /organizations: {len(orgs_res.json()['items'])} organizations found.")

    # Repositories
    repos_res = client.get("/api/v1/repositories")
    assert repos_res.status_code == 200
    repos = repos_res.json()["items"]
    assert len(repos) >= 1
    repo_id = repos[0]["id"]
    print(f"   GET /repositories: {repos[0]['full_name']} (ID: {repo_id})")

    # Pull Requests
    prs_res = client.get("/api/v1/pull-requests")
    assert prs_res.status_code == 200
    prs = prs_res.json()["items"]
    assert len(prs) >= 1
    pr_id = prs[0]["id"]
    print(f"   GET /pull-requests: PR #{prs[0]['number']} '{prs[0]['title']}'")

    # Pull Request Detail
    pr_detail_res = client.get(f"/api/v1/pull-requests/{pr_id}")
    assert pr_detail_res.status_code == 200
    assert pr_detail_res.json()["latest_review_status"] == "COMPLETED"
    print(f"   GET /pull-requests/{pr_id}: Latest Review Status = COMPLETED")

    # Review Job & Artifacts
    artifacts_res = client.get(f"/api/v1/review-jobs/{job_id}/artifacts")
    assert artifacts_res.status_code == 200
    artifacts = artifacts_res.json()
    assert len(artifacts) >= 2, f"Expected at least 2 artifacts (including PR_METADATA and DIFF), found {len(artifacts)}"
    types = [a["artifact_type"] for a in artifacts]
    print(f"   GET /review-jobs/{job_id}/artifacts: Stored artifacts: {types}")
    diff_art = next(a for a in artifacts if a["artifact_type"] == "DIFF")
    meta_art = next(a for a in artifacts if a["artifact_type"] == "PR_METADATA")
    assert "diff --git" in diff_art["content"]
    assert meta_art["metadata_json"]["github_pr_id"] is not None

    print("\n==================================================================")
    print("    PHASE 1 VERIFICATION PASSED: ALL SUCCESS CRITERIA MET!        ")
    print("==================================================================")


if __name__ == "__main__":
    main()
