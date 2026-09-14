"""MCP Principal and Role definitions for API service."""

import enum

from pydantic import BaseModel


class PrincipalRole(enum.StrEnum):
    MEMBER = "MEMBER"
    REVIEWER = "REVIEWER"
    ADMIN = "ADMIN"
    AGENT = "AGENT"
    SERVICE = "SERVICE"


class Principal(BaseModel):
    """Authenticated caller principal representation."""

    principal_id: str
    role: PrincipalRole
    organization_id: str
    is_ai_agent: bool = False
    metadata: dict[str, str] = {}
