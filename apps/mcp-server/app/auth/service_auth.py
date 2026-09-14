"""Service authentication and principal context for MCP Server."""

import enum
import hmac
import os
from typing import NamedTuple

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


class ServiceAuthResult(NamedTuple):
    authenticated: bool
    principal: Principal | None
    error_message: str | None


class ServiceAuthenticator:
    """Validates service tokens and authenticates internal callers to the MCP server."""

    def __init__(self, secret_key: str | None = None) -> None:
        self.secret_key = secret_key or os.getenv("MCP_SERVICE_TOKEN", "dev-mcp-service-token")

    def authenticate_request(
        self,
        token: str | None,
        caller_principal_id: str = "agent-reviewer",
        caller_role: str = "AGENT",
        organization_id: str = "default-org",
        is_ai_agent: bool = True,
    ) -> ServiceAuthResult:
        """Authenticate caller via bearer service token or mutual header."""
        if not token:
            return ServiceAuthResult(
                authenticated=False,
                principal=None,
                error_message="Missing Authorization credentials.",
            )

        token_clean = token.replace("Bearer ", "").strip()

        # Constant-time comparison against configured service secret
        if not hmac.compare_digest(token_clean, self.secret_key):
            return ServiceAuthResult(
                authenticated=False,
                principal=None,
                error_message="Invalid service token or credentials.",
            )

        try:
            role_enum = PrincipalRole(caller_role.upper())
        except ValueError:
            role_enum = PrincipalRole.MEMBER

        principal = Principal(
            principal_id=caller_principal_id,
            role=role_enum,
            organization_id=organization_id,
            is_ai_agent=is_ai_agent,
        )

        return ServiceAuthResult(
            authenticated=True,
            principal=principal,
            error_message=None,
        )
