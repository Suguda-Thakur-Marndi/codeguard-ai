"""MCP Tool Registry managing tool metadata, schemas, risk levels, and dispatch."""

from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import BaseModel

from app.schemas.tools import ToolRiskLevel


class ToolDefinition:
    """Registered MCP Tool definition."""

    def __init__(
        self,
        name: str,
        description: str,
        input_schema: type[BaseModel],
        risk_level: ToolRiskLevel,
        handler: Callable[..., Awaitable[Any]],
        requires_approval: bool = False,
    ) -> None:
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.risk_level = risk_level
        self.handler = handler
        self.requires_approval = requires_approval

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema.model_json_schema(),
            "risk_level": self.risk_level.value,
            "requires_approval": self.requires_approval,
        }


class ToolRegistry:
    """Central registry of verified MCP tools."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, Any]]:
        return [tool.to_dict() for tool in self._tools.values()]
