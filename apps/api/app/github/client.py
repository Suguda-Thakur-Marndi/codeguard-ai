"""GitHub API Client infrastructure adapter."""

import asyncio
from typing import Any

import httpx

from app.core.config import settings
from app.core.exceptions import (
    GitHubAPIError,
    GitHubNotFoundError,
    GitHubRateLimitError,
)
from app.core.logging import TimingLogger, logger
from app.github.auth import GitHubAppAuth


class GitHubClient:
    """Production GitHub client adapter using GitHub App installation tokens."""

    def __init__(
        self,
        auth: GitHubAppAuth | None = None,
        base_url: str = "https://api.github.com",
    ):
        self.auth = auth or GitHubAppAuth()
        self.base_url = base_url.rstrip("/")

    async def _get_auth_headers(
        self, installation_id: int, accept: str = "application/vnd.github+json"
    ) -> dict[str, str]:
        """Obtain authorization headers for an installation."""
        token = await self.auth.get_installation_access_token(installation_id)
        return {
            "Authorization": f"Bearer {token}",
            "Accept": accept,
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "CodeGuard-AI/0.1.0",
        }

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        installation_id: int,
        accept: str = "application/vnd.github+json",
        max_retries: int = 3,
        **kwargs: Any,
    ) -> httpx.Response:
        """Execute HTTP request with rate limit handling and exponential backoff."""
        url = f"{self.base_url}/{path.lstrip('/')}"

        # If in dev/test and mock token is active, return dummy response for standalone test runs
        if not self.auth.private_key and settings.APP_ENV in ("development", "test"):
            # Return realistic mock responses for testing
            return self._build_mock_response(method, path, accept)

        for attempt in range(1, max_retries + 1):
            headers = await self._get_auth_headers(installation_id, accept=accept)
            try:
                with TimingLogger(
                    "github_api_request",
                    {"method": method, "path": path, "attempt": attempt},
                ):
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.request(
                            method, url, headers=headers, **kwargs
                        )

                # Check for rate limiting
                if response.status_code in (403, 429) and "rate limit" in response.text.lower():
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < max_retries:
                        logger.warning(
                            f"GitHub rate limit hit on {path}. Backing off {retry_after}s"
                        )
                        await asyncio.sleep(min(retry_after, 5))  # Cap backoff in tests
                        continue
                    raise GitHubRateLimitError(retry_after=retry_after)

                # Check 404 Not Found
                if response.status_code == 404:
                    raise GitHubNotFoundError(
                        resource=path, details={"response": response.text}
                    )

                # Retry server errors (5xx)
                if response.status_code >= 500:
                    if attempt < max_retries:
                        backoff = 2**attempt
                        logger.warning(
                            f"GitHub server error {response.status_code} on {path}. Retrying in {backoff}s"
                        )
                        await asyncio.sleep(backoff)
                        continue
                    raise GitHubAPIError(
                        f"GitHub server error {response.status_code}: {response.text}",
                        status_code=502,
                        retryable=True,
                    )

                if response.status_code >= 400:
                    raise GitHubAPIError(
                        f"GitHub API error {response.status_code}: {response.text}",
                        status_code=response.status_code,
                        retryable=False,
                    )

                return response

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                if attempt < max_retries:
                    backoff = 2**attempt
                    logger.warning(
                        f"Network error contacting GitHub API on {path}: {exc}. Retrying in {backoff}s"
                    )
                    await asyncio.sleep(backoff)
                    continue
                raise GitHubAPIError(
                    f"Failed to connect to GitHub API: {str(exc)}",
                    status_code=504,
                    retryable=True,
                ) from exc

        raise GitHubAPIError("Max retries exceeded", status_code=502)

    def _build_mock_response(self, method: str, path: str, accept: str) -> httpx.Response:
        """Construct mock responses for local offline dev/testing."""
        if "pulls/" in path and accept == "application/vnd.github.v3.diff":
            diff_content = (
                "diff --git a/src/index.ts b/src/index.ts\n"
                "index 1234567..89abcde 100644\n"
                "--- a/src/index.ts\n"
                "+++ b/src/index.ts\n"
                "@@ -1,5 +1,6 @@\n"
                " export function hello(): string {\n"
                "-  return 'hello';\n"
                "+  // Production greeting\n"
                "+  return 'hello world';\n"
                " }\n"
            )
            return httpx.Response(200, text=diff_content)

        if "pulls/" in path and "files" in path:
            return httpx.Response(
                200,
                json=[
                    {
                        "filename": "src/index.ts",
                        "status": "modified",
                        "additions": 2,
                        "deletions": 1,
                        "changes": 3,
                    }
                ],
            )

        if "pulls/" in path:
            return httpx.Response(
                200,
                json={
                    "id": 12345678,
                    "number": 42,
                    "title": "Add production greeting feature",
                    "body": "Implements improved greeting response.",
                    "state": "open",
                    "draft": False,
                    "user": {"login": "octocat"},
                    "base": {"sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e"},
                    "head": {"sha": "9e5c45b5b57875f334f61aebed695e2e4193db5f"},
                },
            )

        if "reviews" in path and method == "POST":
            return httpx.Response(
                200,
                json={
                    "id": 998877,
                    "user": {"login": "codeguard-ai[bot]"},
                    "body": "CodeGuard AI Verified Review",
                    "state": "COMMENTED",
                    "html_url": f"https://github.com/{path.lstrip('/')}",
                    "comment_ids": [101, 102],
                },
            )

        if "comments" in path:
            return httpx.Response(
                200,
                json=[
                    {"id": 101, "path": "src/index.ts", "line": 1, "body": "Verified finding"}
                ],
            )

        if "repos/" in path:
            return httpx.Response(
                200,
                json={
                    "id": 98765432,
                    "name": "Hello-World",
                    "full_name": "octocat/Hello-World",
                    "private": False,
                    "default_branch": "main",
                },
            )

        return httpx.Response(200, json={})

    async def get_repository(
        self, owner: str, repo: str, installation_id: int
    ) -> dict[str, Any]:
        """Fetch repository details from GitHub."""
        path = f"/repos/{owner}/{repo}"
        response = await self._request_with_retry("GET", path, installation_id)
        return response.json()

    async def get_pull_request(
        self, owner: str, repo: str, pull_number: int, installation_id: int
    ) -> dict[str, Any]:
        """Fetch pull request metadata from GitHub."""
        path = f"/repos/{owner}/{repo}/pulls/{pull_number}"
        response = await self._request_with_retry("GET", path, installation_id)
        return response.json()

    async def get_pull_request_diff(
        self, owner: str, repo: str, pull_number: int, installation_id: int
    ) -> str:
        """Fetch raw unified diff for a pull request."""
        path = f"/repos/{owner}/{repo}/pulls/{pull_number}"
        response = await self._request_with_retry(
            "GET", path, installation_id, accept="application/vnd.github.v3.diff"
        )
        return response.text

    async def list_pull_request_files(
        self, owner: str, repo: str, pull_number: int, installation_id: int
    ) -> list[dict[str, Any]]:
        """List files changed in a pull request."""
        path = f"/repos/{owner}/{repo}/pulls/{pull_number}/files"
        response = await self._request_with_retry("GET", path, installation_id)
        return response.json()

    async def create_pull_request_review(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        payload: dict[str, Any],
        installation_id: int | None = None,
    ) -> dict[str, Any]:
        """Submit an atomic pull request review with inline comments to GitHub."""
        path = f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews"
        inst_id = installation_id or 1
        response = await self._request_with_retry("POST", path, inst_id, json=payload)
        return response.json()

    async def get_pull_request_review_comments(
        self,
        owner: str,
        repo: str,
        pull_number: int,
        review_id: int,
        installation_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieve comments created on a specific pull request review."""
        path = f"/repos/{owner}/{repo}/pulls/{pull_number}/reviews/{review_id}/comments"
        inst_id = installation_id or 1
        response = await self._request_with_retry("GET", path, inst_id)
        return response.json()
