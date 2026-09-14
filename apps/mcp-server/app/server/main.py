"""MCP Server FastAPI application exposing authenticated tool boundary."""

import time
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError

from app.audit.audit_logger import MCPAuditLogger
from app.auth.service_auth import Principal, ServiceAuthenticator
from app.policies.policy_engine import PolicyDecision, PolicyEngine
from app.schemas.tools import MCPResultEnvelope, ToolError, ToolMetadata
from app.tools import default_registry

app = FastAPI(
    title="CodeGuard AI MCP Server",
    version="1.0.0",
    description="Dedicated Model Context Protocol (MCP) tool gateway with zero-trust policy engine.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

authenticator = ServiceAuthenticator()
audit_logger = MCPAuditLogger()


async def get_authenticated_principal(
    authorization: str | None = Header(default=None),
    x_principal_id: str = Header(default="agent-reviewer"),
    x_principal_role: str = Header(default="AGENT"),
    x_organization_id: str = Header(default="default-org"),
    x_is_ai_agent: bool = Header(default=True),
) -> Principal:
    """Dependency validating service authentication credentials."""
    res = authenticator.authenticate_request(
        token=authorization,
        caller_principal_id=x_principal_id,
        caller_role=x_principal_role,
        organization_id=x_organization_id,
        is_ai_agent=x_is_ai_agent,
    )
    if not res.authenticated or res.principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=res.error_message or "Authentication required.",
        )
    return res.principal


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "mcp-server"}


@app.get("/mcp/v1/tools")
async def list_tools(
    principal: Principal = Depends(get_authenticated_principal),
) -> dict[str, Any]:
    """Return all available MCP tools and their parameter schemas."""
    return {"tools": default_registry.list_tools()}


@app.post("/mcp/v1/tools/{tool_name}/execute")
async def execute_tool(
    tool_name: str,
    payload: dict[str, Any],
    principal: Principal = Depends(get_authenticated_principal),
) -> MCPResultEnvelope[Any]:
    """
    Execute an MCP tool under strict governance:
    Authentication -> Input Validation -> Policy Engine -> Execution -> Audit Log.
    """
    exec_id = str(uuid.uuid4())
    started_at = datetime.now(UTC)
    t0 = time.perf_counter()

    tool = default_registry.get(tool_name)
    if tool is None:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        audit_logger.record_event(
            principal_id=principal.principal_id,
            organization_id=principal.organization_id,
            tool_name=tool_name,
            risk_level="HIGH_RISK",
            authorization_decision="DENY",
            started_at=started_at,
            execution_status="DENIED",
            duration_ms=duration_ms,
            error_code="UNKNOWN_TOOL",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tool '{tool_name}' is not registered on this MCP server.",
        )

    # 1. Strict input schema validation
    try:
        validated_input = tool.input_schema.model_validate(payload.get("parameters", {}))
        params = validated_input.model_dump()
    except ValidationError as val_err:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        audit_logger.record_event(
            principal_id=principal.principal_id,
            organization_id=principal.organization_id,
            tool_name=tool_name,
            risk_level=tool.risk_level.value,
            authorization_decision="INVALID_INPUT",
            started_at=started_at,
            execution_status="FAILED",
            duration_ms=duration_ms,
            error_code="SCHEMA_VALIDATION_ERROR",
        )
        return MCPResultEnvelope(
            success=False,
            data=None,
            error=ToolError(
                code="INVALID_INPUT",
                message="Tool parameter schema validation failed.",
                details={"errors": val_err.errors()},
            ),
            metadata=ToolMetadata(tool_name=tool_name, execution_id=exec_id, duration_ms=duration_ms),
        )

    # 2. Deterministic Policy Evaluation
    org_policy = payload.get("org_policy", {})
    approval_record = payload.get("approval_record")
    findings_metadata = payload.get("findings_metadata", [])
    context = payload.get("context", {})

    authz = PolicyEngine.evaluate(
        principal=principal,
        organization_id=principal.organization_id,
        repository_id=params.get("repository_id"),
        tool_name=tool_name,
        parameters=params,
        org_policy=org_policy,
        approval_record=approval_record,
        findings_metadata=findings_metadata,
    )

    if authz.decision != PolicyDecision.ALLOW:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        audit_logger.record_event(
            principal_id=principal.principal_id,
            organization_id=principal.organization_id,
            repository_id=params.get("repository_id"),
            tool_name=tool_name,
            risk_level=authz.risk_level.value,
            authorization_decision=authz.decision.value,
            started_at=started_at,
            execution_status="BLOCKED",
            duration_ms=duration_ms,
            error_code=authz.decision.value,
            metadata={"reason": authz.reason},
        )
        err_code = "APPROVAL_REQUIRED" if authz.decision == PolicyDecision.REQUIRE_APPROVAL else "ACCESS_DENIED"
        return MCPResultEnvelope(
            success=False,
            data=None,
            error=ToolError(code=err_code, message=authz.reason, details={"decision": authz.decision.value}),
            metadata=ToolMetadata(tool_name=tool_name, execution_id=exec_id, duration_ms=duration_ms),
        )

    # 3. Tool Execution
    try:
        data = await tool.handler(params, context)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        audit_logger.record_event(
            principal_id=principal.principal_id,
            organization_id=principal.organization_id,
            repository_id=params.get("repository_id"),
            tool_name=tool_name,
            risk_level=authz.risk_level.value,
            authorization_decision=authz.decision.value,
            approval_id=approval_record.get("id") if approval_record else None,
            started_at=started_at,
            execution_status="SUCCESS",
            duration_ms=duration_ms,
            metadata={"head_sha": params.get("head_sha")},
        )

        return MCPResultEnvelope(
            success=True,
            data=data,
            error=None,
            metadata=ToolMetadata(tool_name=tool_name, execution_id=exec_id, duration_ms=duration_ms),
        )
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000.0
        audit_logger.record_event(
            principal_id=principal.principal_id,
            organization_id=principal.organization_id,
            repository_id=params.get("repository_id"),
            tool_name=tool_name,
            risk_level=authz.risk_level.value,
            authorization_decision=authz.decision.value,
            started_at=started_at,
            execution_status="FAILED",
            duration_ms=duration_ms,
            error_code="EXECUTION_FAILURE",
            metadata={"error": str(exc)},
        )
        return MCPResultEnvelope(
            success=False,
            data=None,
            error=ToolError(code="TOOL_EXECUTION_ERROR", message=str(exc)),
            metadata=ToolMetadata(tool_name=tool_name, execution_id=exec_id, duration_ms=duration_ms),
        )


@app.get("/mcp/v1/audit")
async def get_audit_trail(
    organization_id: str | None = None,
    repository_id: str | None = None,
    tool_name: str | None = None,
    limit: int = 100,
    principal: Principal = Depends(get_authenticated_principal),
) -> dict[str, Any]:
    """Retrieve immutable audit records."""
    org_filter = organization_id or principal.organization_id
    records = audit_logger.list_events(
        organization_id=org_filter,
        repository_id=repository_id,
        tool_name=tool_name,
        limit=limit,
    )
    return {"items": [r.model_dump() for r in records], "total": len(records)}
