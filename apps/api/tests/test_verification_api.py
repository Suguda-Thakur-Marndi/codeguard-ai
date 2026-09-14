"""Tests for Phase 4 verification and adversarial judge API endpoints."""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.repositories.review_finding_repo import ReviewFindingRepository
from app.models.organization import Organization
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.review_finding import (
    FindingCategory,
    FindingSeverity,
    FindingStatus,
    ReviewFindingModel,
)
from app.models.review_job import ReviewJob, ReviewJobStatus


def seed_entities_with_findings(db_session: Session):
    """Seed DB with org, repo, pr, job, and a verified finding."""
    org = Organization(
        github_installation_id=555,
        github_account_id=666,
        github_account_login="security-inc",
        account_type="Organization",
    )
    db_session.add(org)
    db_session.flush()

    repo = Repository(
        organization_id=org.id,
        github_repo_id=777,
        owner="security-inc",
        name="crypto-service",
        full_name="security-inc/crypto-service",
        default_branch="main",
        is_private=True,
    )
    db_session.add(repo)
    db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_id=888,
        number=42,
        title="Add refund endpoint",
        description="Implements refund functionality.",
        author_login="dev",
        base_sha="1111111111111111111111111111111111111111",
        head_sha="2222222222222222222222222222222222222222",
        state="open",
        is_draft=False,
    )
    db_session.add(pr)
    db_session.flush()

    job = ReviewJob(
        pull_request_id=pr.id,
        status=ReviewJobStatus.COMPLETED,
        trigger="webhook:opened",
    )
    db_session.add(job)
    db_session.flush()

    finding = ReviewFindingModel(
        review_job_id=job.id,
        agent_name="security_agent",
        file_path="src/crypto.py",
        line_number=50,
        category=FindingCategory.SECURITY,
        severity=FindingSeverity.HIGH,
        title="Insecure IV generation in AES CBC mode",
        description="Static IV used across encrypt calls.",
        impact="Insecure cryptography enables ciphertext decryption.",
        recommendation="Use os.urandom(16) to generate a unique IV per encryption.",
        confidence=0.92,
        status=FindingStatus.PUBLISHABLE,
        original_severity="HIGH",
        final_severity="HIGH",
        specialist_confidence=0.90,
        judge_confidence=0.95,
        final_confidence=0.93,
        source_agents=["security_agent"],
        evidence=[{"type": "CODE", "content": "iv = b'0'*16"}],
    )
    db_session.add(finding)
    db_session.flush()

    # Seed an evidence item and a verification event
    finding_repo = ReviewFindingRepository(db_session)
    finding_repo.create_finding_evidence(
        {
            "finding_id": finding.id,
            "evidence_type": "CODE",
            "file_path": "src/crypto.py",
            "line_start": 50,
            "line_end": 50,
            "description": "Static IV assignment",
            "snippet": "iv = b'0'*16",
        }
    )
    finding_repo.record_verification_event(
        review_job_id=str(job.id),
        event_type="candidate_generated",
        finding_id=finding.id,
        metadata={"agent": "security_agent"},
    )

    db_session.commit()
    return {"job": job, "finding": finding}


def test_get_review_job_verification_summary(client: TestClient, db_session: Session):
    """GET /api/v1/review-jobs/{id}/verification returns summary metrics."""
    data = seed_entities_with_findings(db_session)
    job_id = str(data["job"].id)

    response = client.get(f"/api/v1/review-jobs/{job_id}/verification")
    assert response.status_code == 200
    res = response.json()
    assert "candidate_count" in res
    assert "publishable_count" in res
    assert res["publishable_count"] == 1


def test_get_review_job_judge_runs(client: TestClient, db_session: Session):
    """GET /api/v1/review-jobs/{id}/judge returns judge runs."""
    data = seed_entities_with_findings(db_session)
    job_id = str(data["job"].id)

    response = client.get(f"/api/v1/review-jobs/{job_id}/judge")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_review_job_validation_scenarios(client: TestClient, db_session: Session):
    """GET /api/v1/review-jobs/{id}/validation returns validation scenarios."""
    data = seed_entities_with_findings(db_session)
    job_id = str(data["job"].id)

    response = client.get(f"/api/v1/review-jobs/{job_id}/validation")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_finding_detail_and_evidence(client: TestClient, db_session: Session):
    """GET /api/v1/findings/{id} and /evidence returns finding with grounding evidence."""
    data = seed_entities_with_findings(db_session)
    finding_id = str(data["finding"].id)

    # Finding Detail
    res1 = client.get(f"/api/v1/findings/{finding_id}")
    assert res1.status_code == 200
    detail = res1.json()
    assert detail["id"] == finding_id
    assert detail["title"] == "Insecure IV generation in AES CBC mode"
    assert detail["status"] == "PUBLISHABLE"
    assert detail["source_agents"] == ["security_agent"]

    # Finding Evidence
    res2 = client.get(f"/api/v1/findings/{finding_id}/evidence")
    assert res2.status_code == 200
    evidence = res2.json()
    assert len(evidence) >= 1
    assert evidence[0]["evidence_type"] == "CODE"


def test_get_finding_history(client: TestClient, db_session: Session):
    """GET /api/v1/findings/{id}/history returns immutable audit trail events."""
    data = seed_entities_with_findings(db_session)
    finding_id = str(data["finding"].id)

    res = client.get(f"/api/v1/findings/{finding_id}/history")
    assert res.status_code == 200
    events = res.json()
    assert len(events) >= 1
    assert events[0]["event_type"] == "candidate_generated"


def test_finding_actions_verify_and_rerun(client: TestClient, db_session: Session):
    """POST /api/v1/findings/{id}/verify and /rerun-validation record events and return refreshed finding."""
    data = seed_entities_with_findings(db_session)
    finding_id = str(data["finding"].id)

    res_verify = client.post(f"/api/v1/findings/{finding_id}/verify")
    assert res_verify.status_code == 200
    assert res_verify.json()["id"] == finding_id

    res_rerun = client.post(f"/api/v1/findings/{finding_id}/rerun-validation")
    assert res_rerun.status_code == 200
    assert res_rerun.json()["id"] == finding_id
