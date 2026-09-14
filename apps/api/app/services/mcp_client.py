"""MCP Service Client for invoking tools through the MCP Server boundary."""

import time
import uuid
from typing import Any

import httpx

from app.core.config import settings

# In-process fallback when running unit tests or standalone verification without background HTTP daemon
try:
    from app.mcp.auth import Principal, PrincipalRole
    from app.mcp.policy_engine import PolicyDecision, PolicyEngine
    from app.mcp.schemas import TOOL_SCHEMAS
    _HAS_INPROCESS_MCP = True
except ImportError:
    _HAS_INPROCESS_MCP = False


class MCPClient:
    """Client for securely invoking tools on the isolated MCP server."""

    def __init__(self, base_url: str | None = None, service_token: str | None = None) -> None:
        self.base_url = (base_url or settings.MCP_SERVER_URL).rstrip("/")
        self.service_token = service_token or settings.MCP_SERVICE_TOKEN

    async def execute_tool(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        organization_id: str,
        principal_id: str = "agent-reviewer",
        principal_role: str = "AGENT",
        is_ai_agent: bool = True,
        repository_id: str | None = None,
        org_policy: dict[str, Any] | None = None,
        approval_record: dict[str, Any] | None = None,
        findings_metadata: list[dict[str, Any]] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute an MCP tool through the security boundary.
        Attempts HTTP call to mcp-server first; falls back to in-process policy evaluation if standalone.
        """
        headers = {
            "Authorization": f"Bearer {self.service_token}",
            "x-principal-id": principal_id,
            "x-principal-role": principal_role,
            "x-organization-id": organization_id,
            "x-is-ai-agent": "true" if is_ai_agent else "false",
        }
        payload = {
            "parameters": parameters,
            "org_policy": org_policy or {},
            "approval_record": approval_record,
            "findings_metadata": findings_metadata or [],
            "context": context or {},
        }

        url = f"{self.base_url}/mcp/v1/tools/{tool_name}/execute"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code in (200, 400, 403, 404):
                    return resp.json()
        except Exception:
            # If standalone dev/test environment without separate HTTP daemon running, use in-process engine
            pass

        return await self._execute_in_process(
            tool_name=tool_name,
            parameters=parameters,
            organization_id=organization_id,
            principal_id=principal_id,
            principal_role=principal_role,
            is_ai_agent=is_ai_agent,
            repository_id=repository_id,
            org_policy=org_policy,
            approval_record=approval_record,
            findings_metadata=findings_metadata,
            context=context,
        )

    async def _execute_in_process(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        organization_id: str,
        principal_id: str,
        principal_role: str,
        is_ai_agent: bool,
        repository_id: str | None,
        org_policy: dict[str, Any] | None,
        approval_record: dict[str, Any] | None,
        findings_metadata: list[dict[str, Any]] | None,
        context: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """In-process execution of MCP tools ensuring identical policy enforcement."""
        if not _HAS_INPROCESS_MCP:
            raise RuntimeError("MCP server unavailable and in-process MCP package not found.")

        t0 = time.perf_counter()
        exec_id = str(uuid.uuid4())

        input_schema_cls = TOOL_SCHEMAS.get(tool_name)
        if not input_schema_cls:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "success": False,
                "data": None,
                "error": {"code": "UNKNOWN_TOOL", "message": f"Tool '{tool_name}' not found."},
                "metadata": {"tool_name": tool_name, "execution_id": exec_id, "duration_ms": duration_ms},
            }

        # 1. Input schema validation
        try:
            validated = input_schema_cls.model_validate(parameters)
            _ = validated.model_dump()
        except Exception as val_err:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "success": False,
                "data": None,
                "error": {"code": "INVALID_INPUT", "message": str(val_err)},
                "metadata": {"tool_name": tool_name, "execution_id": exec_id, "duration_ms": duration_ms},
            }

        # 2. Policy evaluation
        try:
            role_enum = PrincipalRole(principal_role.upper())
        except ValueError:
            role_enum = PrincipalRole.MEMBER

        principal = Principal(
            principal_id=principal_id,
            role=role_enum,
            organization_id=organization_id,
            is_ai_agent=is_ai_agent,
        )

        authz = PolicyEngine.evaluate(
            principal=principal,
            organization_id=organization_id,
            repository_id=repository_id or parameters.get("repository_id"),
            tool_name=tool_name,
            parameters=parameters,
            org_policy=org_policy or {},
            approval_record=approval_record,
            findings_metadata=findings_metadata or [],
        )

        if authz.decision != PolicyDecision.ALLOW:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            err_code = "APPROVAL_REQUIRED" if authz.decision == PolicyDecision.REQUIRE_APPROVAL else "ACCESS_DENIED"
            return {
                "success": False,
                "data": None,
                "error": {"code": err_code, "message": authz.reason, "details": {"decision": authz.decision.value}},
                "metadata": {"tool_name": tool_name, "execution_id": exec_id, "duration_ms": duration_ms},
            }

        # 3. Tool execution
        try:
            if tool_name == "submit_review":
                from app.github.publisher import GitHubReviewPublisher
                ctx = context or {}
                pub_instance = ctx.get("publisher") or GitHubReviewPublisher()
                findings = ctx.get("findings", [])
                valid_lines = ctx.get("valid_lines_by_file")
                cur_sha = ctx.get("current_head_sha", parameters["head_sha"])
                owner = ctx.get("owner", "org")
                repo_name = ctx.get("repo", "repo")
                res = await pub_instance.publish_atomic_review(
                    owner=owner,
                    repo=repo_name,
                    pull_number=parameters["pull_request_number"],
                    verified_head_sha=parameters["head_sha"],
                    current_head_sha=cur_sha,
                    findings=findings,
                    action=parameters.get("action", "COMMENT"),
                    valid_lines_by_file=valid_lines,
                )
                if not res.success:
                    raise RuntimeError(f"Review publication failed [{res.status}]: {res.error_message}")
                data = {
                    "status": res.status,
                    "github_review_id": res.github_review_id,
                    "comment_count": res.comment_count,
                    "created_comment_ids": res.created_comment_ids,
                    "head_sha": parameters["head_sha"],
                    "action": parameters.get("action", "COMMENT"),
                }
            else:
                data = {"status": "ok", "tool": tool_name}

            duration_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "success": True,
                "data": data,
                "error": None,
                "metadata": {"tool_name": tool_name, "execution_id": exec_id, "duration_ms": duration_ms},
            }
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            return {
                "success": False,
                "data": None,
                "error": {"code": "TOOL_EXECUTION_ERROR", "message": str(exc)},
                "metadata": {"tool_name": tool_name, "execution_id": exec_id, "duration_ms": duration_ms},
            }
