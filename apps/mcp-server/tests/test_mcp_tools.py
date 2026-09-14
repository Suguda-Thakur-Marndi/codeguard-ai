"""Unit tests for MCP tool definitions, registry, schemas, and execution."""

import pytest

from app.auth.service_auth import PrincipalRole, ServiceAuthenticator
from app.schemas.tools import (
    GetPullRequestInput,
    ToolRiskLevel,
)
from app.tools import default_registry


@pytest.mark.asyncio
async def test_tool_registry_registration() -> None:
    tools = default_registry.list_tools()
    tool_names = [t["name"] for t in tools]

    assert "get_pull_request" in tool_names
    assert "get_pull_request_diff" in tool_names
    assert "get_file" in tool_names
    assert "run_validation" in tool_names
    assert "submit_review" in tool_names
    assert len(tools) >= 13


@pytest.mark.asyncio
async def test_read_tools_execution() -> None:
    tool = default_registry.get("get_pull_request")
    assert tool is not None
    assert tool.risk_level == ToolRiskLevel.READ_ONLY

    # Valid input validation
    valid_params = GetPullRequestInput(repository_id="repo-1", pull_request_number=42).model_dump()
    res = await tool.handler(valid_params)
    assert res["number"] == 42
    assert res["state"] == "open"


@pytest.mark.asyncio
async def test_service_authentication() -> None:
    auth = ServiceAuthenticator(secret_key="test-secret")

    # Missing token
    res_missing = auth.authenticate_request(None)
    assert not res_missing.authenticated

    # Bad token
    res_bad = auth.authenticate_request("Bearer wrong-secret")
    assert not res_bad.authenticated

    # Valid token
    res_good = auth.authenticate_request(
        "Bearer test-secret",
        caller_principal_id="user-123",
        caller_role="REVIEWER",
        organization_id="org-abc",
        is_ai_agent=False,
    )
    assert res_good.authenticated
    assert res_good.principal is not None
    assert res_good.principal.role == PrincipalRole.REVIEWER
    assert not res_good.principal.is_ai_agent
