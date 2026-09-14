"""Immutable Audit Logger for MCP tool execution and policy decisions."""

import re
import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

SECRET_PATTERNS = [
    re.compile(r"(?i)(bearer\s+)[a-zA-Z0-9_\-\.]{10,}"),
    re.compile(r"(?i)(api[_-]?key\s*[:=]\s*['\"]?)[a-zA-Z0-9_\-]{10,}"),
    re.compile(r"(?i)(github[_-]?token\s*[:=]\s*['\"]?)[a-zA-Z0-9_\-]{10,}"),
    re.compile(r"(?i)(private[_-]?key\s*[:=]\s*['\"]?)[^\n'\"]+"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"ghs_[a-zA-Z0-9]{36}"),
]


def sanitize_secrets(value: Any) -> Any:
    """Recursively sanitize any sensitive tokens or secrets from metadata."""
    if isinstance(value, str):
        cleaned = value
        for pattern in SECRET_PATTERNS:
            if pattern.groups > 0:
                cleaned = pattern.sub(r"\g<1>[REDACTED_SECRET]", cleaned)
            else:
                cleaned = pattern.sub("[REDACTED_SECRET]", cleaned)
        return cleaned
    elif isinstance(value, dict):
        return {k: sanitize_secrets(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_secrets(item) for item in value]
    return value


class AuditEvent(BaseModel):
    """Immutable audit record structure."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    principal_id: str
    organization_id: str
    repository_id: str | None = None
    tool_name: str
    resource_type: str = "repository"
    resource_id: str | None = None
    risk_level: str
    authorization_decision: str
    approval_id: str | None = None
    execution_status: str = "SUCCESS"
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    error_code: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class MCPAuditLogger:
    """In-memory and persistent append-only audit store."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def record_event(
        self,
        principal_id: str,
        organization_id: str,
        tool_name: str,
        risk_level: str,
        authorization_decision: str,
        started_at: datetime,
        completed_at: datetime | None = None,
        repository_id: str | None = None,
        resource_type: str = "repository",
        resource_id: str | None = None,
        approval_id: str | None = None,
        execution_status: str = "SUCCESS",
        duration_ms: float = 0.0,
        error_code: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        clean_metadata = sanitize_secrets(metadata or {})
        event = AuditEvent(
            principal_id=principal_id,
            organization_id=organization_id,
            repository_id=repository_id,
            tool_name=tool_name,
            resource_type=resource_type,
            resource_id=resource_id,
            risk_level=risk_level,
            authorization_decision=authorization_decision,
            approval_id=approval_id,
            execution_status=execution_status,
            started_at=started_at,
            completed_at=completed_at or datetime.now(UTC),
            duration_ms=duration_ms,
            error_code=error_code,
            metadata_json=clean_metadata,
        )
        self._events.append(event)
        return event

    def list_events(
        self,
        organization_id: str | None = None,
        repository_id: str | None = None,
        tool_name: str | None = None,
        limit: int = 100,
    ) -> list[AuditEvent]:
        res = self._events
        if organization_id:
            res = [e for e in res if e.organization_id == organization_id]
        if repository_id:
            res = [e for e in res if e.repository_id == repository_id]
        if tool_name:
            res = [e for e in res if e.tool_name == tool_name]
        return list(reversed(res))[:limit]
