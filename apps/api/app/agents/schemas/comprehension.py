"""Pydantic schema for Comprehension Agent output."""

from pydantic import BaseModel, Field


class ComprehensionResult(BaseModel):
    """Structured understanding of Pull Request changes, architectural impact, and risk areas."""

    intent: str = Field(
        ...,
        description="High-level developer intent and purpose of the Pull Request",
    )
    summary: str = Field(
        ...,
        description="Concise 2-3 sentence overview of the code changes and affected subsystems",
    )
    functional_changes: list[str] = Field(
        default_factory=list,
        description="List of user-facing or behavior-altering functional changes",
    )
    refactors: list[str] = Field(
        default_factory=list,
        description="List of code restructurings that do not change external behavior",
    )
    changed_components: list[str] = Field(
        default_factory=list,
        description="Modules, packages, or services modified in this PR",
    )
    affected_interfaces: list[str] = Field(
        default_factory=list,
        description="Public API endpoints, function signatures, or contracts modified",
    )
    risk_areas: list[str] = Field(
        default_factory=list,
        description="Identified operational, security, contract, or performance risk dimensions",
    )
    relevant_symbols: list[str] = Field(
        default_factory=list,
        description="Primary symbols (classes, functions, methods) modified or referenced",
    )

    # Classification flags for deterministic risk routing
    is_documentation_only: bool = Field(
        default=False,
        description="True if PR only touches markdown, documentation, or text comments without executable code changes",
    )
    has_security_impact: bool = Field(
        default=False,
        description="True if PR touches auth, credentials, payment, crypto, raw queries, or untrusted user input handling",
    )
    has_database_or_api_impact: bool = Field(
        default=False,
        description="True if PR alters database models, queries, or API controllers/endpoints",
    )
    has_performance_impact: bool = Field(
        default=False,
        description="True if PR touches high-throughput loops, unindexed queries, caching, or heavy batch jobs",
    )
