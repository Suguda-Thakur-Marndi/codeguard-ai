"""Seed script to populate SQLite development database with sample repositories, PRs, and review jobs."""

import os
import sys
from datetime import UTC, datetime

# Ensure apps/api is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api")))

from app.db.session import SessionLocal
from app.models.agent_run import AgentRun
from app.models.agent_trace import AgentTrace
from app.models.organization import Organization
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.review_finding import ReviewFindingModel
from app.models.review_job import ReviewJob, ReviewJobStatus


def seed():
    session = SessionLocal()
    try:
        # Check if already seeded
        existing_org = session.query(Organization).first()
        if existing_org:
            print("Database already contains data, skipping seed.")
            return

        print("Seeding development data...")

        # 1. Organization
        org = Organization(
            github_installation_id=123456,
            github_account_id=987654,
            github_account_login="codeguard-ai",
            account_type="Organization",
        )
        session.add(org)
        session.flush()

        # 2. Repositories
        repos = [
            Repository(
                organization_id=org.id,
                github_repo_id=101,
                owner="codeguard-ai",
                name="auth-service",
                full_name="codeguard-ai/auth-service",
                default_branch="main",
                is_private=True,
            ),
            Repository(
                organization_id=org.id,
                github_repo_id=102,
                owner="codeguard-ai",
                name="payment-gateway",
                full_name="codeguard-ai/payment-gateway",
                default_branch="main",
                is_private=True,
            ),
            Repository(
                organization_id=org.id,
                github_repo_id=103,
                owner="codeguard-ai",
                name="code-intelligence-core",
                full_name="codeguard-ai/code-intelligence-core",
                default_branch="main",
                is_private=False,
            ),
        ]
        session.add_all(repos)
        session.flush()

        # 3. Pull Requests
        prs = [
            PullRequest(
                repository_id=repos[0].id,
                github_pr_id=201,
                number=42,
                title="Migrate session auth to OAuth2 JWT Bearer tokens",
                description="Refactors authentication flow to use asymmetric RS256 token verification.",
                author_login="alex-dev",
                base_sha="a1b2c3d4e5f678901234567890abcdef12345678",
                head_sha="f6e5d4c3b2a109876543210987654321fedcba09",
                state="open",
                is_draft=False,
            ),
            PullRequest(
                repository_id=repos[1].id,
                github_pr_id=202,
                number=88,
                title="Add webhook idempotency key validation",
                description="Prevents duplicate charge processing by enforcing unique idempotency headers.",
                author_login="sara-fintech",
                base_sha="3333333333333333333333333333333333333333",
                head_sha="4444444444444444444444444444444444444444",
                state="open",
                is_draft=False,
            ),
            PullRequest(
                repository_id=repos[2].id,
                github_pr_id=203,
                number=12,
                title="Optimize Tree-sitter AST symbol cache traversal",
                description="Reduces dependency parsing latency by 45% using indexed symbol tables.",
                author_login="marcus-arch",
                base_sha="5555555555555555555555555555555555555555",
                head_sha="6666666666666666666666666666666666666666",
                state="closed",
                is_draft=False,
            ),
        ]
        session.add_all(prs)
        session.flush()

        # 4. Review Jobs
        jobs = [
            ReviewJob(
                pull_request_id=prs[0].id,
                status=ReviewJobStatus.COMPLETED,
                trigger="webhook:opened",
                total_tokens=2450,
                estimated_cost=0.0042,
                agents_executed=["security", "bug", "architecture"],
            ),
            ReviewJob(
                pull_request_id=prs[1].id,
                status=ReviewJobStatus.COMPLETED,
                trigger="webhook:synchronize",
                total_tokens=1820,
                estimated_cost=0.0031,
                agents_executed=["security", "performance"],
            ),
        ]
        session.add_all(jobs)
        session.flush()

        # 5. Agent Runs & Findings
        run1 = AgentRun(
            review_job_id=jobs[0].id,
            agent_name="security",
            agent_version="1.0.0",
            model_name="gemini-2.5-pro",
            prompt_version="security.v1",
            status="COMPLETED",
            input_tokens=1500,
            output_tokens=350,
            total_tokens=1850,
            estimated_cost=0.0032,
            latency_ms=920.0,
            retry_count=0,
        )
        run2 = AgentRun(
            review_job_id=jobs[0].id,
            agent_name="architecture",
            agent_version="1.0.0",
            model_name="gemini-2.5-flash",
            prompt_version="arch.v1",
            status="COMPLETED",
            input_tokens=500,
            output_tokens=100,
            total_tokens=600,
            estimated_cost=0.0010,
            latency_ms=450.0,
            retry_count=0,
        )
        session.add_all([run1, run2])
        session.flush()

        finding1 = ReviewFindingModel(
            review_job_id=jobs[0].id,
            agent_run_id=run1.id,
            file_path="src/auth/jwt.py",
            line_number=52,
            side="RIGHT",
            category="SECURITY",
            severity="HIGH",
            title="Algorithm Confusion Vulnerability in JWT Decode",
            description="The jwt.decode() call does not enforce algorithms=['RS256'], allowing attackers to forge tokens using HMAC-SHA256 with the public key as HMAC secret.",
            impact="Full authentication bypass allowing arbitrary token forgery as superadmin.",
            recommendation="Explicitly restrict allowed algorithms to ['RS256'] in jwt.decode().",
            confidence=0.96,
            evidence=[{"type": "CODE", "file": "src/auth/jwt.py", "description": "jwt.decode(token, verify=False)"}],
            agent_name="security",
            status="VALID",
        )
        finding2 = ReviewFindingModel(
            review_job_id=jobs[0].id,
            agent_run_id=run2.id,
            file_path="src/auth/session.py",
            line_number=88,
            side="RIGHT",
            category="ARCHITECTURE",
            severity="MEDIUM",
            title="Leaked Session State Across Request Threads",
            description="Global session dict is shared across asyncio worker threads without thread-local or contextvars isolation.",
            impact="Potential cross-tenant session pollution under concurrent request load.",
            recommendation="Use contextvars.ContextVar for request-scoped session tokens.",
            confidence=0.88,
            evidence=[{"type": "CODE", "file": "src/auth/session.py", "description": "_SESSION_STORE = {}"}],
            agent_name="architecture",
            status="VALID",
        )
        session.add_all([finding1, finding2])

        # 6. Traces
        trace1 = AgentTrace(
            review_job_id=jobs[0].id,
            node_name="specialists_dispatcher_node",
            agent_name="security",
            status="COMPLETED",
            start_time=datetime.now(UTC),
            end_time=datetime.now(UTC),
            duration_ms=920.0,
            model_name="gemini-2.5-pro",
            input_tokens=1500,
            output_tokens=350,
            total_tokens=1850,
            retry_count=0,
        )
        session.add(trace1)

        session.commit()
        print("Successfully seeded development data into SQLite!")

    except Exception as e:
        session.rollback()
        print("Error seeding database:", e)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed()
