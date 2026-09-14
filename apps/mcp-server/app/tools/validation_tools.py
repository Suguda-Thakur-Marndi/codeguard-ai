"""Controlled operational MCP tool handlers for validation."""

from typing import Any


async def handle_run_validation(params: dict[str, Any], context: Any = None) -> dict[str, Any]:
    return {
        "status": "PASS",
        "scenario_id": params["scenario_id"],
        "finding_id": params["finding_id"],
        "review_job_id": params["review_job_id"],
        "duration_ms": 42.5,
        "output": "1 passed in 0.04s",
    }
