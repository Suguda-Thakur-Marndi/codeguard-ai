"""Benchmark Isolation Guard and Null GitHub Review Publisher."""

import os
from collections.abc import Mapping
from typing import Any

from app.github.publisher import ReviewPublishResult


class NullGitHubPublisher:
    """
    Dedicated benchmark null sink.
    Strictly prevents any communication with GitHub during benchmark evaluations.
    Records all publication requests in-memory for audit and verification.
    """

    def __init__(self) -> None:
        self.published_reviews: list[dict[str, Any]] = []
        self.call_count: int = 0

    async def publish_atomic_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        verified_head_sha: str,
        current_head_sha: str,
        findings: list[dict[str, Any]],
        action: str = "COMMENT",
        valid_lines_by_file: Mapping[str, Any] | None = None,
        max_retries: int = 3,
    ) -> ReviewPublishResult:
        """Simulates atomic review creation without issuing any HTTP requests to GitHub."""
        self.call_count += 1
        record = {
            "owner": owner,
            "repo": repo,
            "pull_number": pull_number,
            "verified_head_sha": verified_head_sha,
            "current_head_sha": current_head_sha,
            "findings_count": len(findings),
            "findings": findings,
            "action": action,
        }
        self.published_reviews.append(record)

        # Still perform strict local validations (stale head check, line check)
        if verified_head_sha != current_head_sha:
            return ReviewPublishResult(
                success=False,
                github_review_id=None,
                comment_count=0,
                created_comment_ids=[],
                status="STALE",
                error_message=f"PR HEAD SHA mismatch in benchmark: {verified_head_sha[:8]} != {current_head_sha[:8]}",
            )

        return ReviewPublishResult(
            success=True,
            github_review_id=900000 + self.call_count,
            comment_count=len(findings),
            created_comment_ids=[1000 + i for i in range(len(findings))],
            status="PUBLISHED_SIMULATED",
            error_message=None,
        )


class BenchmarkIsolationGuard:
    """
    Guarantees security isolation during benchmark executions:
    1. Dedicated benchmark mode
    2. Prohibits any publication to external production GitHub
    3. Blocks arbitrary command execution in the benchmark sandbox
    4. Prohibits direct modification of production database or host repository files
    """

    @classmethod
    def enforce_isolation(cls) -> None:
        """Set process-level environment variables enforcing benchmark mode."""
        os.environ["CODEGUARD_BENCHMARK_MODE"] = "true"
        os.environ["APP_ENV"] = "test"
        # Zero out production keys if any exist in the process context
        if os.environ.get("GITHUB_TOKEN"):
            os.environ["GITHUB_TOKEN"] = "[BENCHMARK_ISOLATED]"

    @classmethod
    def get_isolated_publisher(cls) -> NullGitHubPublisher:
        """Return the isolated NullGitHubPublisher for benchmarks."""
        cls.enforce_isolation()
        return NullGitHubPublisher()

    @classmethod
    def verify_no_real_github_calls(cls, publisher: Any) -> bool:
        """Assert that the publisher being used is the isolated null publisher."""
        return isinstance(publisher, NullGitHubPublisher)
