"""Controlled operational MCP tool handlers for review submission."""

from typing import Any

from app.github.publisher import GitHubReviewPublisher

publisher = GitHubReviewPublisher()


async def handle_submit_review(params: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    ctx = context or {}
    findings = ctx.get("findings", [])
    valid_lines_by_file = ctx.get("valid_lines_by_file")
    current_head_sha = ctx.get("current_head_sha", params["head_sha"])
    owner = ctx.get("owner", "prod-org")
    repo = ctx.get("repo", "payment-service")

    pub_instance = ctx.get("publisher", publisher)
    res = await pub_instance.publish_atomic_review(
        owner=owner,
        repo=repo,
        pull_number=params["pull_request_number"],
        verified_head_sha=params["head_sha"],
        current_head_sha=current_head_sha,
        findings=findings,
        action=params.get("action", "COMMENT"),
        valid_lines_by_file=valid_lines_by_file,
    )

    if not res.success:
        raise RuntimeError(f"Review publication failed [{res.status}]: {res.error_message}")

    return {
        "status": res.status,
        "github_review_id": res.github_review_id,
        "comment_count": res.comment_count,
        "created_comment_ids": res.created_comment_ids,
        "head_sha": params["head_sha"],
        "action": params.get("action", "COMMENT"),
    }
