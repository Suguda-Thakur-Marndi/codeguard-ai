"""API integration tests for all 10 Code Intelligence endpoints."""

import json

import pytest
from fastapi.testclient import TestClient

from app.models.code_symbol import CodeSymbol
from app.models.file_dependency import FileDependency
from app.models.organization import Organization
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.repository_index import IndexStatus, RepositoryIndex
from app.models.review_artifact import ArtifactType, ReviewArtifact
from app.models.review_job import ReviewJob, ReviewJobStatus


@pytest.fixture
def test_data(db_session):
    org = Organization(
        github_installation_id=111,
        github_account_id=222,
        github_account_login="acme",
    )
    db_session.add(org)
    db_session.flush()

    repo = Repository(
        organization_id=org.id,
        github_repo_id=333,
        owner="acme",
        name="backend",
        full_name="acme/backend",
        default_branch="main",
    )
    db_session.add(repo)
    db_session.flush()

    pr = PullRequest(
        repository_id=repo.id,
        github_pr_id=444,
        number=1,
        title="Add refund support",
        author_login="octocat",
        base_sha="sha_base",
        head_sha="sha_head",
    )
    db_session.add(pr)
    db_session.flush()

    job = ReviewJob(
        pull_request_id=pr.id,
        status=ReviewJobStatus.COMPLETED,
    )
    db_session.add(job)
    db_session.flush()

    # Add RepositoryIndex
    idx = RepositoryIndex(
        repository_id=repo.id,
        commit_sha="sha_head",
        status=IndexStatus.READY,
        files_processed=5,
        metadata_json={"symbols_count": 10},
    )
    db_session.add(idx)

    # Add CodeSymbol
    sym = CodeSymbol(
        repository_id=repo.id,
        commit_sha="sha_head",
        file_path="src/payment.py",
        name="PaymentService.refund",
        kind="METHOD",
        language="python",
        start_line=10,
        end_line=25,
        signature="def refund(self, p_id: str) -> bool",
    )
    db_session.add(sym)

    # Add FileDependency
    dep = FileDependency(
        repository_id=repo.id,
        commit_sha="sha_head",
        source_file="src/payment.py",
        target_file="src/repository.py",
        dependency_type="IMPORTS",
        imported_symbols=["PaymentRepo"],
        line_number=2,
    )
    db_session.add(dep)

    # Add ReviewArtifacts for job
    art_diff = ReviewArtifact(
        review_job_id=job.id,
        artifact_type=ArtifactType.PARSED_DIFF,
        content=json.dumps([
            {
                "file_path": "src/payment.py",
                "old_path": "src/payment.py",
                "new_path": "src/payment.py",
                "change_type": "modified",
                "is_binary": False,
                "hunks": [
                    {
                        "old_start": 10,
                        "old_count": 5,
                        "new_start": 10,
                        "new_count": 6,
                        "lines": [
                            {"type": "ADDED", "new_line": 15, "content": "    # added"}
                        ],
                    }
                ],
            }
        ]),
    )
    db_session.add(art_diff)

    art_chunks = ReviewArtifact(
        review_job_id=job.id,
        artifact_type=ArtifactType.AST_CHUNKS,
        content=json.dumps([
            {
                "id": "chk_1",
                "file_path": "src/payment.py",
                "language": "python",
                "node_type": "function_definition",
                "symbol_name": "PaymentService.refund",
                "start_line": 10,
                "end_line": 25,
                "signature": "def refund(self, p_id: str) -> bool",
                "source_code": "def refund(): pass",
            }
        ]),
    )
    db_session.add(art_chunks)

    art_lines = ReviewArtifact(
        review_job_id=job.id,
        artifact_type=ArtifactType.CHANGED_LINE_INDEX,
        content=json.dumps({
            "src/payment.py": {
                "RIGHT": [10, 11, 15],
                "LEFT": [10, 11],
            }
        }),
    )
    db_session.add(art_lines)

    db_session.commit()
    return {"org": org, "repo": repo, "pr": pr, "job": job, "sym": sym}


def test_repository_index_endpoints(client: TestClient, test_data):
    repo_id = test_data["repo"].id

    # 1. GET /repositories/{id}/index
    res = client.get(f"/api/v1/repositories/{repo_id}/index")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "READY"
    assert data["commit_sha"] == "sha_head"
    assert data["files_processed"] == 5

    # 2. POST /repositories/{id}/index
    post_res = client.post(
        f"/api/v1/repositories/{repo_id}/index",
        json={"commit_sha": "sha_head", "force_reindex": False},
    )
    assert post_res.status_code == 200
    assert post_res.json()["status"] == "READY"


def test_repository_symbols_and_detail_endpoints(client: TestClient, test_data):
    repo_id = test_data["repo"].id
    sym_id = test_data["sym"].id

    # 3. GET /repositories/{id}/symbols
    res = client.get(f"/api/v1/repositories/{repo_id}/symbols")
    assert res.status_code == 200
    payload = res.json()
    assert payload["total"] >= 1
    assert payload["items"][0]["name"] == "PaymentService.refund"

    # With filters
    kind_res = client.get(f"/api/v1/repositories/{repo_id}/symbols?kind=METHOD")
    assert kind_res.status_code == 200
    assert len(kind_res.json()["items"]) == 1

    # 4. GET /repositories/{id}/symbols/{symbol_id}
    detail_res = client.get(f"/api/v1/repositories/{repo_id}/symbols/{sym_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["signature"] == "def refund(self, p_id: str) -> bool"


def test_repository_file_symbols_and_dependencies(client: TestClient, test_data):
    repo_id = test_data["repo"].id

    # 5. GET /repositories/{id}/files/{file_path}/symbols
    res = client.get(f"/api/v1/repositories/{repo_id}/files/src/payment.py/symbols")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 1
    assert items[0]["name"] == "PaymentService.refund"

    # 6. GET /repositories/{id}/files/{file_path}/dependencies
    dep_res = client.get(f"/api/v1/repositories/{repo_id}/files/src/payment.py/dependencies")
    assert dep_res.status_code == 200
    deps = dep_res.json()
    assert len(deps) >= 1
    assert deps[0]["target_file"] == "src/repository.py"


def test_repository_context_endpoint(client: TestClient, test_data):
    repo_id = test_data["repo"].id

    # 7. GET /repositories/{id}/context
    res = client.get(
        f"/api/v1/repositories/{repo_id}/context?changed_file=src/payment.py&changed_symbol=PaymentService.refund"
    )
    assert res.status_code == 200
    ctx = res.json()
    assert ctx["changed_file"] == "src/payment.py"
    assert ctx["changed_symbol"] == "PaymentService.refund"
    assert len(ctx["ranked_items"]) >= 1


def test_review_job_code_intelligence_endpoints(client: TestClient, test_data):
    job_id = test_data["job"].id

    # 8. GET /review-jobs/{job_id}/diff
    diff_res = client.get(f"/api/v1/review-jobs/{job_id}/diff")
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert len(diff_data) == 1
    assert diff_data[0]["file_path"] == "src/payment.py"

    # 9. GET /review-jobs/{job_id}/chunks
    chunks_res = client.get(f"/api/v1/review-jobs/{job_id}/chunks")
    assert chunks_res.status_code == 200
    chunks_data = chunks_res.json()
    assert len(chunks_data) == 1
    assert chunks_data[0]["symbol_name"] == "PaymentService.refund"

    # 10. GET /review-jobs/{job_id}/changed-lines
    lines_res = client.get(f"/api/v1/review-jobs/{job_id}/changed-lines")
    assert lines_res.status_code == 200
    lines_data = lines_res.json()
    assert "src/payment.py" in lines_data["index"]
    assert 15 in lines_data["index"]["src/payment.py"]["RIGHT"]
