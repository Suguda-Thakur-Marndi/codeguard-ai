"""Read-only MCP tool handlers."""

from typing import Any

from app.code.adapters import CodeIntelligenceAdapter

code_adapter = CodeIntelligenceAdapter()


async def handle_get_pull_request(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    return {
        "repository_id": params["repository_id"],
        "number": params["pull_request_number"],
        "title": "Add production payment processing",
        "state": "open",
        "author": "dev-engineer",
        "head_sha": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "base_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    }


async def handle_get_pull_request_diff(params: dict[str, Any], context: Any = None) -> str:
    return (
        "diff --git a/src/services/payment_service.py b/src/services/payment_service.py\n"
        "--- a/src/services/payment_service.py\n"
        "+++ b/src/services/payment_service.py\n"
        "@@ -140,4 +140,4 @@\n"
        "+    refund = gateway.refund()\n"
    )


async def handle_get_pull_request_files(params: dict[str, Any], context: Any = None) -> list[dict[str, Any]]:
    return [
        {
            "filename": "src/services/payment_service.py",
            "status": "modified",
            "additions": 1,
            "deletions": 0,
        }
    ]


async def handle_get_repository(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    return {
        "id": params["repository_id"],
        "name": "payment-service",
        "default_branch": "main",
    }


async def handle_get_file(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    return await code_adapter.get_file(
        repository_id=params["repository_id"],
        commit_sha=params["commit_sha"],
        file_path=params["file_path"],
    )


async def handle_get_symbol(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    return await code_adapter.get_symbol(
        repository_id=params["repository_id"],
        commit_sha=params["commit_sha"],
        symbol_name=params["symbol_name"],
    )


async def handle_find_references(params: dict[str, Any], context: Any = None) -> list[dict[str, Any]]:
    return await code_adapter.find_references(
        repository_id=params["repository_id"],
        commit_sha=params["commit_sha"],
        symbol_name=params["symbol_name"],
    )


async def handle_get_dependencies(params: dict[str, Any], context: Any = None) -> list[str]:
    return await code_adapter.get_dependencies(
        repository_id=params["repository_id"],
        commit_sha=params["commit_sha"],
        file_path=params["file_path"],
    )


async def handle_get_tests(params: dict[str, Any], context: Any = None) -> list[str]:
    return await code_adapter.get_tests(
        repository_id=params["repository_id"],
        commit_sha=params["commit_sha"],
        target_file=params["target_file"],
    )


async def handle_get_review_findings(params: dict[str, Any], context: Any = None) -> list[dict[str, Any]]:
    return [
        {
            "id": "finding-1",
            "review_job_id": params["review_job_id"],
            "title": "Missing Authorization Check",
            "severity": "HIGH",
            "status": "PUBLISHABLE",
            "file_path": "src/services/payment_service.py",
            "line_number": 142,
        }
    ]


async def handle_get_review_evidence(params: dict[str, Any], context: Any = None) -> list[dict[str, Any]]:
    return [
        {
            "finding_id": params["finding_id"],
            "type": "CODE",
            "file": "src/services/payment_service.py",
            "line_start": 142,
            "line_end": 142,
            "description": "Unprotected call to refund",
        }
    ]
