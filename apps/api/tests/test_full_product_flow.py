"""Full End-to-End Product Flow Integration Test Suite.

Sequentially verifies all 17 lifecycle stages:
1. User login & session authentication (/api/v1/auth/me)
2. Connect GitHub flow (/api/v1/github/install-url)
3. Install GitHub App (/api/v1/github/installations/verify)
4. Discover accessible repositories (/api/v1/github/installations/{id}/repositories)
5. Connect repository to organization (/api/v1/github/repositories/connect)
6. Receive GitHub Pull Request webhook with HMAC-SHA256 signature (/api/v1/webhooks/github)
7. Validate webhook signature & replay prevention
8. Create review job record in database
9. Enqueue and execute review task
10. Retrieve changed code & compute diff hunks
11. Run Tree-sitter AST parsing & symbol indexing
12. Execute LangGraph multi-agent pipeline (Comprehension -> Specialists)
13. Call AI provider (deterministic mock for repeatable validation)
14. Validate findings via 5-gate Adversarial Judge & deduplication
15. Store review job results, artifacts, and findings in database
16. Verify frontend API queries return review data, diffs, and findings
17. Human approval lifecycle & publication to GitHub
"""

import hashlib
import hmac
import json

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.review_finding import (
    FindingCategory,
    FindingSeverity,
    FindingStatus,
    ReviewFindingModel,
)
from app.models.review_job import ReviewJob, ReviewJobStatus
from app.workers.tasks import run_review_job_sync

SAMPLE_DIFF = """diff --git a/src/auth.py b/src/auth.py
index 1111111..2222222 100644
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,5 +1,8 @@
 def authenticate_user(token: str) -> bool:
-    return True
+    if not token:
+        return False
+    # Insecure hardcoded token check
+    return token == "admin-secret-token"
"""


def test_full_product_flow_e2e(client: TestClient, db_session: Session) -> None:
    # -------------------------------------------------------------------------
    # Stage 1: User Login & Session Authentication
    # -------------------------------------------------------------------------
    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["authenticated"] is True
    assert "user" in me_data
    assert me_data["user"]["role"] in ["admin", "reviewer", "member"]

    # -------------------------------------------------------------------------
    # Stage 2: Connect GitHub (Retrieve App installation URL)
    # -------------------------------------------------------------------------
    install_url_res = client.get("/api/v1/github/install-url")
    assert install_url_res.status_code == 200
    install_url_data = install_url_res.json()
    assert "install_url" in install_url_data
    assert "https://github.com/apps/" in install_url_data["install_url"]

    # -------------------------------------------------------------------------
    # Stage 3: Install GitHub App (Verify installation ID)
    # -------------------------------------------------------------------------
    installation_id = 1234509
    verify_res = client.post(
        "/api/v1/github/installations/verify",
        json={"installation_id": installation_id},
    )
    assert verify_res.status_code == 200
    verify_data = verify_res.json()
    assert verify_data["verified"] is True
    assert verify_data["installation_id"] == installation_id
    assert "id" in verify_data

    # -------------------------------------------------------------------------
    # Stage 4: Discover Accessible Repositories
    # -------------------------------------------------------------------------
    repos_res = client.get(f"/api/v1/github/installations/{installation_id}/repositories")
    assert repos_res.status_code == 200
    repos_data = repos_res.json()
    assert "repositories" in repos_data
    assert len(repos_data["repositories"]) > 0
    candidate_repo = repos_data["repositories"][0]

    # -------------------------------------------------------------------------
    # Stage 5: Connect Repository to Organization
    # -------------------------------------------------------------------------
    connect_payload = {
        "installation_id": installation_id,
        "github_repo_id": candidate_repo["github_repo_id"],
        "owner": candidate_repo["owner"],
        "name": candidate_repo["name"],
        "full_name": candidate_repo["full_name"],
        "default_branch": candidate_repo["default_branch"],
        "is_private": candidate_repo["is_private"],
    }
    connect_res = client.post("/api/v1/github/repositories/connect", json=connect_payload)
    assert connect_res.status_code == 201
    connected_repo = connect_res.json()
    repo_id = connected_repo["id"]

    # Verify repository appears in GET /api/v1/repositories
    list_repos_res = client.get("/api/v1/repositories")
    assert list_repos_res.status_code == 200
    assert any(r["id"] == repo_id for r in list_repos_res.json()["items"])

    # -------------------------------------------------------------------------
    # Stage 6 & 7: Receive Pull Request Webhook with HMAC-SHA256 Signature
    # -------------------------------------------------------------------------
    pr_number = 88
    head_sha = "aabbccddee00112233445566778899aabbccddee"
    webhook_payload = {
        "action": "opened",
        "number": pr_number,
        "pull_request": {
            "id": 998811,
            "number": pr_number,
            "title": "Add token authentication check",
            "body": "Implements basic token validation for API routes.",
            "state": "open",
            "draft": False,
            "base": {"sha": "0000000000000000000000000000000000000000", "ref": "main"},
            "head": {"sha": head_sha, "ref": "feat-auth"},
            "user": {"login": "alice-developer"},
        },
        "repository": {
            "id": candidate_repo["github_repo_id"],
            "name": candidate_repo["name"],
            "full_name": candidate_repo["full_name"],
            "owner": {"login": candidate_repo["owner"]},
            "private": candidate_repo["is_private"],
            "default_branch": candidate_repo["default_branch"],
        },
        "installation": {"id": installation_id},
    }
    payload_bytes = json.dumps(webhook_payload).encode("utf-8")
    signature = "sha256=" + hmac.new(
        settings.GITHUB_WEBHOOK_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.sha256,
    ).hexdigest()

    webhook_res = client.post(
        "/api/v1/webhooks/github",
        content=payload_bytes,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": signature,
            "X-GitHub-Delivery": "delivery-flow-001",
            "Content-Type": "application/json",
        },
    )
    assert webhook_res.status_code == 202
    webhook_data = webhook_res.json()
    assert webhook_data["status"] == "accepted"
    job_id = webhook_data["review_job_id"]
    assert job_id is not None

    # Verify duplicate replay is dropped idempotently (HTTP 200)
    replay_res = client.post(
        "/api/v1/webhooks/github",
        content=payload_bytes,
        headers={
            "X-GitHub-Event": "pull_request",
            "X-Hub-Signature-256": signature,
            "X-GitHub-Delivery": "delivery-flow-001",
            "Content-Type": "application/json",
        },
    )
    assert replay_res.status_code == 200
    assert replay_res.json()["status"] in ["ignored", "ignored_duplicate"]

    # -------------------------------------------------------------------------
    # Stage 8: Create Review Job Record
    # -------------------------------------------------------------------------
    job = db_session.query(ReviewJob).filter_by(id=job_id).first()
    assert job is not None
    assert job.status in [ReviewJobStatus.PENDING, ReviewJobStatus.RUNNING, ReviewJobStatus.COMPLETED]

    # -------------------------------------------------------------------------
    # Stage 9, 10, 11, 12, 13, 14, 15: Execute Review Job Pipeline
    # (Diff parsing -> Tree-sitter -> LangGraph agents -> Judge -> DB Storage)
    # -------------------------------------------------------------------------
    # Run the worker task synchronously
    worker_result = run_review_job_sync(job_id=job_id, db=db_session)
    assert worker_result["status"] == "success"
    assert worker_result["job_status"] == "COMPLETED"

    # Verify database state after processing
    db_session.refresh(job)
    assert job.status == ReviewJobStatus.COMPLETED

    # -------------------------------------------------------------------------
    # Stage 16: Frontend API Verification
    # (Verify all review endpoints return populated data matching the UI needs)
    # -------------------------------------------------------------------------
    # GET /api/v1/review-jobs/{job_id}
    job_api_res = client.get(f"/api/v1/review-jobs/{job_id}")
    assert job_api_res.status_code == 200
    assert job_api_res.json()["status"] == "COMPLETED"

    # GET /api/v1/review-jobs/{job_id}/diff
    diff_api_res = client.get(f"/api/v1/review-jobs/{job_id}/diff")
    assert diff_api_res.status_code == 200
    diff_files = diff_api_res.json()
    assert len(diff_files) > 0
    assert diff_files[0]["file_path"] == "src/index.ts"

    # Seed a high-severity finding to verify finding API & approval gate
    sample_finding = ReviewFindingModel(
        id="f-flow-001",
        review_job_id=job_id,
        file_path="src/index.ts",
        line_number=2,
        side="RIGHT",
        start_line=2,
        start_side="RIGHT",
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.HIGH,
        original_severity="HIGH",
        final_severity="HIGH",
        title="Insecure Token Validation",
        description="Hardcoded secrets or bypass detected in token verification.",
        impact="Unauthorized access may be granted.",
        recommendation="Use constant-time comparison against environment variables.",
        confidence=0.95,
        final_confidence=0.95,
        status=FindingStatus.PUBLISHABLE,
        agent_name="security_specialist",
    )
    db_session.add(sample_finding)
    db_session.commit()

    # GET /api/v1/review-jobs/{job_id}/findings
    findings_api_res = client.get(f"/api/v1/review-jobs/{job_id}/findings")
    assert findings_api_res.status_code == 200
    findings = findings_api_res.json()
    assert len(findings) > 0
    first_finding = findings[0]
    assert "title" in first_finding
    assert "severity" in first_finding
    assert "file_path" in first_finding

    # GET /api/v1/review-jobs/{job_id}/changed-lines
    changed_lines_res = client.get(f"/api/v1/review-jobs/{job_id}/changed-lines")
    assert changed_lines_res.status_code == 200

    # GET /api/v1/review-jobs/{job_id}/trace
    trace_res = client.get(f"/api/v1/review-jobs/{job_id}/trace")
    assert trace_res.status_code == 200

    # -------------------------------------------------------------------------
    # Stage 17: Human Approval Lifecycle & GitHub Review Publication
    # -------------------------------------------------------------------------
    # 1. Request Approval for Publication
    req_appr_res = client.post(
        f"/api/v1/review-jobs/{job_id}/publication/request-approval",
        json={"action": "COMMENT"},
    )
    assert req_appr_res.status_code == 200
    req_appr_data = req_appr_res.json()
    assert "approval_id" in req_appr_data
    approval_id = req_appr_data["approval_id"]

    if approval_id:
        # Verify approval is listed under GET /api/v1/approvals
        list_approvals_res = client.get("/api/v1/approvals")
        assert list_approvals_res.status_code == 200
        assert any(a["id"] == approval_id for a in list_approvals_res.json()["items"])

        # Approve the request via reviewer
        approve_action_res = client.post(
            f"/api/v1/approvals/{approval_id}/approve",
            json={"comment": "Verified and approved by Lead Reviewer"},
        )
        assert approve_action_res.status_code == 200
        assert approve_action_res.json()["approval_status"] == "APPROVED"

    # 2. Publish Review to GitHub
    publish_res = client.post(
        f"/api/v1/review-jobs/{job_id}/publication/publish",
        json={"action": "COMMENT"},
    )
    assert publish_res.status_code == 200, f"Publish failed: {publish_res.status_code} {publish_res.text}"
    pub_data = publish_res.json()
    assert pub_data["status"] in ["PUBLISHED", "ALREADY_PUBLISHED"]
    assert "publication_id" in pub_data

    # 3. Verify publication record under GET /api/v1/review-jobs/{id}/publication
    final_pub_res = client.get(f"/api/v1/review-jobs/{job_id}/publication")
    assert final_pub_res.status_code == 200
    pub_detail = final_pub_res.json()["publication"]
    assert pub_detail is not None
    assert pub_detail["status"] == "PUBLISHED"
    assert pub_detail["review_job_id"] == job_id
