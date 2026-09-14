"""Tool Execution Audit ORM model for immutable MCP activity tracking."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, UUIDPrimaryKeyMixin


class ToolExecutionAudit(Base, UUIDPrimaryKeyMixin):
    """Append-only audit record for all MCP tool executions and policy decisions."""

    __tablename__ = "tool_execution_audit"

    principal_id: Mapped[str] = mapped_column(
        String(100), index=True, nullable=False
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), index=True, nullable=False
    )
    repository_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    tool_name: Mapped[str] = mapped_column(
        String(100), index=True, nullable=False
    )
    resource_type: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    resource_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    risk_level: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    authorization_decision: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    approval_id: Mapped[str | None] = mapped_column(
        String(36), index=True, nullable=True
    )
    execution_status: Mapped[str] = mapped_column(
        String(50), default="SUCCESS", index=True, nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    duration_ms: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    error_code: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_tool_audit_org_tool", "organization_id", "tool_name"),
        Index("ix_tool_audit_created_at", "created_at"),
    )
